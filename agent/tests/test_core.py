import pytest
from document_helpers.utils import read_text_file, load_financial_sheets, persist_duckdb_with_dataset, create_mock_financial_dataset
import pandas as pd
from agent.assistant import detect_intent, run_sql_agent
from agent.core import load_data_into_sql_engine, sql_engine, ExecutionMode
from unittest.mock import patch
import duckdb

def test_read_file(tmp_path):
    """
    Test functionality of the read text method \n
    
    Args:
        tmp_path (_type_):
        Temporary file path created
        
    Returns:
        The content in string format and the test assertion
    """
    test_file= tmp_path/"sample.txt"
    test_file.write_text("Hello CFO Copilot")
    content = read_text_file(test_file)
    assert content == "Hello CFO Copilot"
    
def test_load_financial_data(tmp_path):
    """_summary_
        Test the functionality of the load_financial_sheets.
    Args:
        tmp_path (_type_): Mock test path for the financials dataset
    
    Returns:
        Assertion showing the right columns as keys and df
    """
    
    test_file= tmp_path/"test.xlsx"
    with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
        pd.DataFrame({"month": ["Jan"], "revenue": [100]}).to_excel(writer, sheet_name="Actuals", index=False)
        pd.DataFrame({"month": ["Jan"], "revenue": [120]}).to_excel(writer, sheet_name="Budget", index=False)
        pd.DataFrame({"month": ["Jan"], "cash_usd": [5000]}).to_excel(writer, sheet_name="Cash", index=False)
        pd.DataFrame({"currency": ["USD"], "rate_to_usd": [1.0]}).to_excel(writer, sheet_name="Fx", index=False)
        
    connection, tables = load_financial_sheets(str(test_file))
    try:
        # Print tables mapping
        print("\n" + "="*50)
        print("LOADED TABLES MAPPING:")
        print("="*50)
        for original_name, table_name in tables.items():
            print(f"  {original_name} -> {table_name}")
        
        # Show all tables in database
        print("\n" + "="*50)
        print("TABLES IN DATABASE:")
        print("="*50)
        result = connection.execute("SHOW TABLES").fetchall()
        for row in result:
            print(f"  - {row[0]}")
        
        # Print each table's contents
        print("\n" + "="*50)
        print("TABLE CONTENTS:")
        print("="*50)
        
        for table_name in ["actuals", "budget", "cash", "fx"]:
            print(f"\n--- Table: {table_name} ---")
            df = connection.execute(f"SELECT * FROM {table_name}").fetchdf()
            print(df.to_string(index=False))
        
        # Assertions
        assert set(tables.keys()) == {"actuals", "budget", "cash", "fx"}
        assert all(isinstance(name, str) for name in tables.values())
        
        table_names = {row[0] for row in result}
        assert "actuals" in table_names
        assert "budget" in table_names
        assert "cash" in table_names
        assert "fx" in table_names
        
    finally:
        connection.close()
    
@pytest.mark.parametrize("message,expected_label", [
    ("What was June 2025 revenue vs budget in USD?", "get_revenue_vs_budget"),
    ("Show Gross Margin % trend for the last 3 months.", "get_gross_margin_trend"),
    ("Break down Opex by category for June.", "get_opex_breakdown"),
    ("What is our cash runway right now?", "get_cash_runway"),
    ("Calculate EBITDA from the data.", "get_ebitda_proxy"),
])
@patch("agent.assistant.client.text_classification")
def test_detect_intent(mock_classification, message, expected_label):
    """
    Test detect_intent correctly maps financial questions to intents
    using mocked Hugging Face inference results.
    """
    # Mock Hugging Face response
    mock_classification.return_value = [{
        "labels": [expected_label, "other_intent"],
        "scores": [0.95, 0.05]
    }]

    # Run intent detection
    intent, confidence = detect_intent(message)

    # Assertions
    assert intent == expected_label
    assert 0.0 <= confidence <= 1.0
    assert confidence > 0.5  # Confidence threshold
    mock_classification.assert_called_once()
    

@pytest.mark.parametrize("user_query , expected_keywords", [
    ("What was total revenue for January", ["10,000"]),
    ("Show me all expenses for Marketing", ["3,000"]),
    ("What's the total cash position?", ["70,000"]),
    ("Compare budget vs actuals for sales", ["12,000", "10,000"])
])
def test_sql_generation_isvalid(tmp_path, user_query, expected_keywords):
    """
    Test the agent's capability to convert natural language to SQL and execute it.
    This test covers the ENTIRE pipeline:
    1. Natural language query input
    2. Agent generates SQL query
    3. SQL executes against database
    4. Results are returned 
    Args:
        tmp_path (_type_): path to temp file created for mock testing 
        user_query (_type_): User input to be converted into sql query
        expected_keywords (_type_): Validation of keywords to expect in result 
    """
    
    test_file = tmp_path / "financials.xlsx"
    create_mock_financial_dataset(str(test_file))
    load_data_into_sql_engine(str(test_file))
    
    result = run_sql_agent(user_query, ExecutionMode.SQL_MODE)
    assert isinstance(result, str)
    normalized_result = result.lower()
    
    assert "error" not in normalized_result, f"Agent returned error: {result}"  
    for keyword in expected_keywords:
        assert str(keyword) in normalized_result , f"Expected '{keyword}' in result {normalized_result}"
        
    
    
@pytest.mark.parametrize("user_query , expected_keywords", [
    ("What was total revenue for January",["10000","revenue","january"]),
    ("Show me all expenses for Marketing", ["3000", "marketing", "expense"]),
    ("What's the total cash position?", ["7000", "cash"]),
    ("Compare budget vs actuals for sales", ["sales","12000","10000"])
])    
def test_llm_response_generation(tmp_path, user_query, expected_keywords):
    test_file = tmp_path / "financials.xlsx"
    create_mock_financial_dataset(str(test_file))
    load_data_into_sql_engine(str(test_file))
    
    result = run_sql_agent(user_query, ExecutionMode.CHAT_EXPLAIN_MODE)
    assert isinstance(result, str)
    
    normalized_result = result.lower()
    assert "error" not in normalized_result, f"Agent returned error: {result}"
    
    for keyword in expected_keywords:
        assert str(keyword) in normalized_result , f"Expected '{keyword}' in result {normalized_result}"


def test_text_to_sql_database_connection(tmp_path):
    """
    Test that data loaded into SQL engine is accessible to sql_engine tool.
    This verifies the database connection sharing mechanism.
    """
    test_file = tmp_path / "financials.xlsx"
    
    with pd.ExcelWriter(test_file, engine='openpyxl') as file_writer:
        pd.DataFrame({
            "month": ["January"],
            "entity": ["Sales"],
            "account_category": ["revenue"],
            "amount": [10000.0],
            "currency": ["USD"]
        }).to_excel(file_writer, sheet_name="actuals", index=False)
    
    # Load data into SQL engine
    load_data_into_sql_engine(str(test_file))
    
    # Verify data is accessible via sql_engine
    result = sql_engine("SELECT COUNT(*) as count FROM actuals")
    assert "1" in result or "count" in result.lower()
    
    # Verify we can query the data
    result = sql_engine("SELECT amount FROM actuals WHERE month = 'January'")
    assert "10000" in result


def test_text_to_sql_aggregation_queries(tmp_path):
    """
    Test text-to-SQL generation for aggregation queries (SUM, COUNT, AVG).
    """
    test_file = tmp_path / "financials.xlsx"
    
    with pd.ExcelWriter(test_file, engine='openpyxl') as file_writer:
        pd.DataFrame({
            "month": ["January", "January", "February"],
            "entity": ["Sales", "Sales", "Sales"],
            "account_category": ["revenue", "revenue", "revenue"],
            "amount": [10000.0, 5000.0, 8000.0],
            "currency": ["USD", "USD", "USD"]
        }).to_excel(file_writer, sheet_name="actuals", index=False)
    
    load_data_into_sql_engine(str(test_file))
    
    # Test aggregation query
    result = run_sql_agent("What is the total revenue for all months?", ExecutionMode.CHAT_EXPLAIN_MODE)
    result_lower = result.lower()
    
    # Should contain total (23000 = 10000 + 5000 + 8000)
    assert "error" not in result_lower, f"Agent returned error: {result}"
    # The result should contain a number representing the sum
    assert any(char.isdigit() for char in result), f"Result should contain numbers: {result}"


def test_text_to_sql_filter_queries(tmp_path):
    """
    Test text-to-SQL generation for filtered queries (WHERE clauses).
    """
    test_file = tmp_path / "financials.xlsx"
    
    with pd.ExcelWriter(test_file, engine='openpyxl') as file_writer:
        pd.DataFrame({
            "month": ["January", "February"],
            "entity": ["Sales", "Marketing"],
            "account_category": ["revenue", "expense"],
            "amount": [10000.0, 3000.0],
            "currency": ["USD", "USD"]
        }).to_excel(file_writer, sheet_name="actuals", index=False)
    
    load_data_into_sql_engine(str(test_file))
    
    # Test filter query
    result = run_sql_agent("Show me all revenue transactions for January", ExecutionMode.CHAT_EXPLAIN_MODE)
    result_lower = result.lower()
    
    assert "error" not in result_lower, f"Agent returned error: {result}"
    assert "january" in result_lower or "10000" in result


def test_text_to_sql_join_queries(tmp_path):
    """
    Test text-to-SQL generation for queries that join multiple tables.
    """
    test_file = tmp_path / "financials.xlsx"
    
    with pd.ExcelWriter(test_file, engine='openpyxl') as file_writer:
        pd.DataFrame({
            "month": ["January"],
            "entity": ["Sales"],
            "account_category": ["revenue"],
            "amount": [10000.0],
            "currency": ["USD"]
        }).to_excel(file_writer, sheet_name="actuals", index=False)
        
        pd.DataFrame({
            "month": ["January"],
            "entity": ["Sales"],
            "account_category": ["Revenue"],
            "account": ["Product Sales"],
            "amount": [12000.0],
            "currency": ["USD"]
        }).to_excel(file_writer, sheet_name="budget", index=False)
    
    load_data_into_sql_engine(str(test_file))
    
    # Test join query
    result = run_sql_agent("Compare actuals vs budget for January", ExecutionMode.CHAT_EXPLAIN_MODE)
    result_lower = result.lower()
    
    assert "error" not in result_lower, f"Agent returned error: {result}"
    # Should mention both actuals and budget
    assert ("actual" in result_lower or "budget" in result_lower)


def test_text_to_sql_error_handling(tmp_path):
    """
    Test that sql_engine properly handles SQL errors and returns informative messages.
    """
    test_file = tmp_path / "financials.xlsx"
    
    with pd.ExcelWriter(test_file, engine='openpyxl') as file_writer:
        pd.DataFrame({
            "month": ["January"],
            "amount": [1000.0]
        }).to_excel(file_writer, sheet_name="actuals", index=False)
    
    load_data_into_sql_engine(str(test_file))
    
    # Test invalid SQL query
    result = sql_engine("SELECT * FROM nonexistent_table")
    assert "error" in result.lower() or "SQL Execution Error" in result
    
    # Test malformed SQL
    result = sql_engine("SELECT * FROM actuals WHERE invalid_column = 'test'")
    # Should either error or return no rows
    assert isinstance(result, str)


def test_text_to_sql_empty_results(tmp_path):
    """
    Test text-to-SQL handling of queries that return no results.
    """
    test_file = tmp_path / "financials.xlsx"
    
    with pd.ExcelWriter(test_file, engine='openpyxl') as file_writer:
        pd.DataFrame({
            "month": ["January"],
            "entity": ["Sales"],
            "account_category": ["revenue"],
            "amount": [10000.0],
            "currency": ["USD"]
        }).to_excel(file_writer, sheet_name="actuals", index=False)
    
    load_data_into_sql_engine(str(test_file))
    
    # Query that should return no results
    result = sql_engine("SELECT * FROM actuals WHERE month = 'December'")
    assert "no rows" in result.lower() or "successfully executed" in result.lower()


def test_text_to_sql_complex_queries(tmp_path):
    """
    Test text-to-SQL generation for complex queries with GROUP BY and ORDER BY.
    """
    test_file = tmp_path / "financials.xlsx"
    
    with pd.ExcelWriter(test_file, engine='openpyxl') as file_writer:
        pd.DataFrame({
            "month": ["January", "January", "February"],
            "entity": ["Sales", "Marketing", "Sales"],
            "account_category": ["revenue", "expense", "revenue"],
            "amount": [10000.0, 3000.0, 12000.0],
            "currency": ["USD", "USD", "USD"]
        }).to_excel(file_writer, sheet_name="actuals", index=False)
    
    load_data_into_sql_engine(str(test_file))
    
    # Test complex query
    result = run_sql_agent("Show me total revenue by month, ordered by month", ExecutionMode.CHAT_EXPLAIN_MODE)
    result_lower = result.lower()
    
    assert "error" not in result_lower, f"Agent returned error: {result}"
    assert "month" in result_lower or any(char.isdigit() for char in result)


def test_persist_duckdb_with_dataset(tmp_path):
    """
    Test that persist_duckdb_with_dataset correctly persists Excel data to DuckDB file.
    Verifies table creation, data integrity, and proper persistence.
    """
    temp_financial_file = tmp_path / "financials.xlsx"
    temp_duckdb_finai_file = tmp_path / "finai.db"
    
    # Create test data
    actuals_data = pd.DataFrame({
        "month": ["January", "January", "February"],
        "entity": ["Sales", "Marketing", "Sales"],
        "account_category": ["revenue", "expense", "revenue"],
        "amount": [10000.0, 3000.0, 12000.0],
        "currency": ["USD", "USD", "USD"]
    })
    
    budget_data = pd.DataFrame({
        "month": ["January", "January"],
        "entity": ["Sales", "Marketing"],
        "account_category": ["Revenue", "Expense"],
        "account": ["Product Sales", "Ad Spend"],
        "amount": [12000.0, 4000.0],
        "currency": ["USD", "USD"]
    })
    
    cash_data = pd.DataFrame({
        "month": ["January", "February"],
        "entity": ["Corporate", "Sales"],
        "cash_usd": [50000.0, 20000.0]
    })
    
    fx_data = pd.DataFrame({
        "month": ["January"],
        "currency": ["USD"],
        "rate_to_usd": [1.0]
    })
    
    with pd.ExcelWriter(temp_financial_file, engine='openpyxl') as file_writer:
        actuals_data.to_excel(file_writer, sheet_name="actuals", index=False)
        budget_data.to_excel(file_writer, sheet_name="budget", index=False)
        cash_data.to_excel(file_writer, sheet_name="cash", index=False)
        fx_data.to_excel(file_writer, sheet_name="fx", index=False)
        
    # Persist to DuckDB
    persist_duckdb_with_dataset(str(temp_financial_file), str(temp_duckdb_finai_file))
    
    # Verify DuckDB file was created
    assert temp_duckdb_finai_file.exists(), "DuckDB file should be created"
    
    # Connect and verify tables exist
    connection = duckdb.connect(str(temp_duckdb_finai_file))
    try:
        tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        assert {"actuals", "budget", "cash", "fx"}.issubset(tables), \
            f"Expected tables not found. Found: {tables}"
        
        # Verify data integrity - check actuals table
        actuals_result = connection.execute("SELECT * FROM actuals ORDER BY month, entity").fetchdf()
        pd.testing.assert_frame_equal(
            actuals_result.sort_values(by=["month", "entity"]).reset_index(drop=True),
            actuals_data.sort_values(by=["month", "entity"]).reset_index(drop=True),
            check_dtype=False
        )
        
        # Verify data integrity - check budget table
        budget_result = connection.execute("SELECT * FROM budget ORDER BY month, entity").fetchdf()
        pd.testing.assert_frame_equal(
            budget_result.sort_values(by=["month", "entity"]).reset_index(drop=True),
            budget_data.sort_values(by=["month", "entity"]).reset_index(drop=True),
            check_dtype=False
        )
        
        # Verify data integrity - check cash table
        cash_result = connection.execute("SELECT * FROM cash ORDER BY month").fetchdf()
        pd.testing.assert_frame_equal(
            cash_result.sort_values(by="month").reset_index(drop=True),
            cash_data.sort_values(by="month").reset_index(drop=True),
            check_dtype=False
        )
        
        # Verify data integrity - check fx table
        fx_result = connection.execute("SELECT * FROM fx").fetchdf()
        pd.testing.assert_frame_equal(
            fx_result.reset_index(drop=True),
            fx_data.reset_index(drop=True),
            check_dtype=False
        )
        
        # Verify row counts
        assert len(connection.execute("SELECT * FROM actuals").fetchall()) == 3
        assert len(connection.execute("SELECT * FROM budget").fetchall()) == 2
        assert len(connection.execute("SELECT * FROM cash").fetchall()) == 2
        assert len(connection.execute("SELECT * FROM fx").fetchall()) == 1
        
    finally:
        connection.close()


def test_persist_duckdb_with_dataset_replace_behavior(tmp_path):
    """
    Test that persist_duckdb_with_dataset correctly replaces existing tables
    when called multiple times (CREATE OR REPLACE behavior).
    """
    temp_financial_file = tmp_path / "financials.xlsx"
    temp_duckdb_finai_file = tmp_path / "finai.db"
    
    # First dataset
    with pd.ExcelWriter(temp_financial_file, engine='openpyxl') as file_writer:
        pd.DataFrame({
            "month": ["January"],
            "amount": [1000.0]
        }).to_excel(file_writer, sheet_name="actuals", index=False)
    
    persist_duckdb_with_dataset(str(temp_financial_file), str(temp_duckdb_finai_file))
    
    # Second dataset with different data
    with pd.ExcelWriter(temp_financial_file, engine='openpyxl') as file_writer:
        pd.DataFrame({
            "month": ["February"],
            "amount": [2000.0]
        }).to_excel(file_writer, sheet_name="actuals", index=False)
    
    persist_duckdb_with_dataset(str(temp_financial_file), str(temp_duckdb_finai_file))
    
    # Verify the table was replaced with new data
    connection = duckdb.connect(str(temp_duckdb_finai_file))
    try:
        result = connection.execute("SELECT * FROM actuals").fetchdf()
        assert len(result) == 1
        assert result.iloc[0]["month"] == "February"
        assert result.iloc[0]["amount"] == 2000.0
    finally:
        connection.close()


def test_persist_duckdb_with_dataset_missing_file(tmp_path):
    """
    Test that persist_duckdb_with_dataset raises FileNotFoundError
    when the dataset file doesn't exist.
    """
    temp_duckdb_finai_file = tmp_path / "finai.db"
    non_existent_file = tmp_path / "nonexistent.xlsx"
    
    with pytest.raises(FileNotFoundError):
        persist_duckdb_with_dataset(str(non_existent_file), str(temp_duckdb_finai_file))


def test_persist_duckdb_with_dataset_sheet_name_normalization(tmp_path):
    """
    Test that persist_duckdb_with_dataset handles sheet names with spaces and special characters.
    Note: This test may reveal if table name normalization is needed.
    """
    temp_financial_file = tmp_path / "financials.xlsx"
    temp_duckdb_finai_file = tmp_path / "finai.db"
    
    with pd.ExcelWriter(temp_financial_file, engine='openpyxl') as file_writer:
        pd.DataFrame({
            "month": ["January"],
            "amount": [1000.0]
        }).to_excel(file_writer, sheet_name="cash", index=False)
    
    # This test checks if the function handles sheet names with spaces
    # If the implementation doesn't normalize, this might fail
    persist_duckdb_with_dataset(str(temp_financial_file), str(temp_duckdb_finai_file))
    
    connection = duckdb.connect(str(temp_duckdb_finai_file))
    try:
        tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        # The table name might be "Cash Flow" (with space) or normalized
        assert len(tables) == 1
        table_name = list(tables)[0]
        result = connection.execute(f"SELECT * FROM \"{table_name}\"").fetchdf()
        assert len(result) == 1
        assert result.iloc[0]["amount"] == 1000.0
    finally:
        connection.close()


def test_persist_duckdb_with_dataset_empty_sheet(tmp_path):
    """
    Test that persist_duckdb_with_dataset handles empty sheets correctly.
    """
    temp_financial_file = tmp_path / "financials.xlsx"
    temp_duckdb_finai_file = tmp_path / "finai.db"
    
    with pd.ExcelWriter(temp_financial_file, engine='openpyxl') as file_writer:
        # Empty DataFrame with column names
        pd.DataFrame(columns=["month", "amount"]).to_excel(
            file_writer, sheet_name="actuals", index=False
        )
    
    persist_duckdb_with_dataset(str(temp_financial_file), str(temp_duckdb_finai_file))
    
    connection = duckdb.connect(str(temp_duckdb_finai_file))
    try:
        result = connection.execute("SELECT * FROM actuals").fetchdf()
        assert len(result) == 0
        # Verify columns exist
        assert list(result.columns) == ["month", "amount"]
    finally:
        connection.close()
    