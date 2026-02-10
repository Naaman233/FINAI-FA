import pandas as pd
from document_helpers.utils import load_data
import os
from dotenv import load_dotenv,find_dotenv

load_data(find_dotenv())

class FinanceTools:
    
    def __init__(self,data):
        data = load_data(os.getenv("FINANCIAL_DATASET_PATH"))
        self.actuals = data["actuals"]
        self.budget = data["budget"]
        self.cash = data["cash"]
        self.fx = data["fx"]
        
    
    def fx_currency_conversion(self, amount: float, currency: str, month: str):
        
        if currency.upper() == "USD":
            return round(amount, 2)
        
        month = str(month).strip()
        currency = currency.upper().strip()
        
        required_columns = {"month","currency","rate_to_usd"}
        for sheet_name, df in [("fx", self.fx)]:
            if not required_columns.issubset(df.columns):
                raise ValueError(f"{sheet_name} is missing required column {required_columns - set(df.columns)}")
        fx_row = (
            self.fx.assign(
                month = lambda x: x["month"].str.lower().str.strip(),
                currency = lambda x: x["currency"].str.lower().str.strip(),
                rate_to_usd = lambda x: x["rate_to_usd"].str.lower().str.strip()
            )
            .query(
                "month == @month and currency == @currency"
            )
        )
        
        if fx_row.empty:
            raise ValueError(f"No FX rate found for {currency} in {month}")
        
        current_rate = fx_row.iloc[0]["rate_to_usd"]
        if current_rate <= 0:
            raise ValueError(f"current rate for {currency} is invalid")
        
        return round(amount * current_rate, 2)
            
            
    def revenue_vs_budget(self, month: str, entity: str):
        """
        Compare actual vs budget for a given month and entity
        Args:
            month (str): The month associated with the given enity
            entity (str): Account entity in question for the fiscal period
        Returns:
            Returns a dictionary breakdown of the financials of the fiscal period
        """
        month = str(month).strip()
        entity = entity.strip().lower()
        
        #Validating required columns exist
        required_columns = {"month","entity","account_category","amount","currency"}
        for sheet_name, df in [("actuals", self.actuals), ("budget", self.budget)]:
            if not required_columns.issubset(df.columns):
                raise ValueError(f"{sheet_name} is missing required column {required_columns - set(df.columns)}")
        actual = (
            self.actuals.assign(
                entity = lambda x: x["entity"].str.lower().str.strip(),
                account_category = lambda x: x["account_category"].str.lower().str.strip(),
                month = lambda x: x["month"].str.lower().str.strip(),
                currency = lambda x: x["currency"].str.lower().str.strip()
            )
            .query(
                "month == @month and entity == @entity and account_category == 'revenue'"
            )["amount"].sum()
        )
        
        budget = (
            self.budget.assign(
                entity = lambda x: x["entity"].str.lower().str.strip(),
                account_category = lambda x: x["account_category"].str.lower().str.strip(),
                month = lambda x: x["month"].str.lower().str.strip(),
                currency = lambda x: x["currency"].str.lower().str.strip()
            )
            .query(
                "month == @month and entity == @entity and account_category == 'revenue'"
            )["amount"].sum()
        )
        
        variance = actual - budget
        variance_percentage = (variance / budget * 100) if budget != 0 else None
        
        return {
            "month" : month,
            "entity": entity,
            "actual_revenue_usd" : round(actual, 2),
            "budgeted_revenue_usd": round(budget, 2),
            "variance_usd": round(variance, 2),
            "variance_percentage": round(variance_percentage, 2) if variance_percentage is not None else None
        }
        
        
        
        
        
            
    
    

    
