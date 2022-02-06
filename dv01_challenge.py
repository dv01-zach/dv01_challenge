import pandas as pd
import glob

def create_table(data_file):
    ''''
    Given csv path data_file, computes a table with the following output fields, grouped by grade as well as with a total:
    - Total Issued - This is the total loan amount in dollars
    - Fully Paid - This is the initial loan amount of all loans which are fully paid in dollars
    - Current - This is the outstanding principal amount on all loans which are current (including grace period) in dollars.
    - Late - This is the outstanding principal amount on all loans which are late in dollars
    - Charged Off (Net) - This is the amount of balance which has been charged off in dollars. This is computed by calculating
      the difference in the original loan amount and the total payments, and adding back in interest and late fees, since they
      do not contribue to reducing the principal owed.
    - Principal Payments Received - This is the amount of principal received. This is computed by taking the original loan amount
      and subtracting the current balance, late balance, and charge offs
    - Interest Payments Received - This is the amount of interest that has been paid
    - Avg. Interest Rate - This is the initial balance-weighted interest rate
    '''
    data = pd.read_csv(data_file,skiprows=1,low_memory=False)
    data_cln = data[~pd.isna(data.grade)].copy()
    
    data_cln["grade2"] = data_cln["grade"]
    data_cln.loc[data_cln.grade.isin(["F","G"]), "grade2"] = "FG"
    
    to_return = pd.DataFrame(index=data_cln.grade2.unique()).sort_index()
    to_return["Total Issued"] = data_cln.groupby("grade2").loan_amnt.sum()
    
    fully_paid = data_cln[data_cln.loan_status == "Fully Paid"]
    to_return["Fully Paid"] = fully_paid.groupby("grade2").loan_amnt.sum()

    current = data_cln[data_cln.loan_status.isin(["Current", "In Grace Period"])]
    to_return["Current"] = current.groupby("grade2").out_prncp.sum()

    late = data_cln[data_cln.loan_status.str.contains("Late") | (data_cln.loan_status == "Default")]
    to_return["Late"] = late.groupby("grade2").out_prncp.sum()

    charged_off = data_cln[data_cln.loan_status == "Charged Off"]
    charge_offs = charged_off.loan_amnt - charged_off.total_pymnt + charged_off.total_rec_int + charged_off.total_rec_late_fee
    to_return["Charged Off (Net)"] = charge_offs.groupby(charged_off.grade2).sum()

    to_return["Principal Payments Received"] = \
        to_return["Total Issued"] - to_return["Current"] - to_return["Late"] - to_return["Charged Off (Net)"]

    to_return["Interest Payments Received"] = data_cln.groupby("grade2").total_rec_int.sum()

    data_cln["int_rate_float"] = data_cln.int_rate.str.strip("%").astype(float) / 100
    data_cln["avg_int_numerator"] = data_cln["int_rate_float"] * data_cln["loan_amnt"]
    to_return["Avg. Interest Rate"] = data_cln.groupby("grade2").avg_int_numerator.sum() / data_cln.groupby("grade2").loan_amnt.sum()

    to_return.loc["All"] = to_return.sum()
    to_return.loc["All","Avg. Interest Rate"] = data_cln.avg_int_numerator.sum() / data_cln.loan_amnt.sum()

    return to_return

def format_table(table):
    ''''
    Given table, formats such that dollar fields are displayed with dollar sign, commas, and rounded to the nearest dollar.
    The one percent field, Avg. Interest Rate is formatted to show as a percent rounded to 2 decimals
    '''
    to_return = table.copy()
    dollar_fmt_cols = ["Total Issued", "Fully Paid", "Current", "Late", "Charged Off (Net)", 
                       "Principal Payments Received", "Interest Payments Received"]
    for col in dollar_fmt_cols:
        to_return[col] = to_return[col].map("${:,.0f}".format)
    to_return["Avg. Interest Rate"] = to_return["Avg. Interest Rate"].map("{:,.2%}".format)
    return to_return

data_files = glob.glob("data/*.csv")
for data_file in data_files:
    table = create_table(data_file)
    table_cln = format_table(table)
    with open(data_file+".md","w") as outfile:
        outfile.write(table_cln.to_markdown())