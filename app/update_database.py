import pandas as pd
import sqlite3
import json
import datetime
import time
import yfinance as yfi
import talib
import warnings
warnings.filterwarnings("ignore")

# retrieve pattern data
with open("dataset/patterns.json") as f:
    patterns = json.load(f)


def get_last_update_time():
    with sqlite3.connect("dataset/ihsg.db") as con:
        return pd.read_sql("SELECT MAX(time_updated) FROM historical", con=con).values[0][0][:19]

def find_patterns(df):
    result = pd.DataFrame(
        columns=[
            "Date",
            "Kode",
            "Pattern",
            "Pattern_Score",
            "Open_Close_Change",
            "High_Low_Change",
        ]
    )
    for attr, pattern in patterns.items():
        scores = getattr(talib, attr)(df["Open"], df["High"], df["Low"], df["Close"])
        mask = scores != 0
        temp_result = df[mask]
        if len(temp_result) > 0:
            temp_result = temp_result.assign(
                Open_Close_Change=(temp_result["Close"] - temp_result["Open"]) / temp_result["Open"],
                High_Low_Change=(temp_result["High"] - temp_result["Low"]) / temp_result["Low"],
                Pattern=[pattern] * len(temp_result),
                Pattern_Score=scores[mask].values,
            )[result.columns]
            result = result.append(temp_result)
    result = result.assign(time_updated = datetime.datetime.now())
    return result


def update_database():

    with sqlite3.connect("dataset/ihsg.db") as con:
        start_date = datetime.datetime.strptime(
            pd.read_sql("SELECT MAX(Date) FROM historical", con=con).values[0][0], 
            "%Y-%m-%d %H:%M:%S"
        )
        start_date += pd.offsets.DateOffset(days=1)
        start_date = datetime.datetime.strftime(start_date, "%Y-%m-%d")
        end_date = datetime.datetime.now()
        if end_date.hour < 15:
            end_date -= pd.offsets.DateOffset(days = 1)

        ihsg = (
            yfi.download("^JKSE", start=start_date, end=end_date, progress=False)
            .dropna()
        )[start_date:end_date]
        print("New Data = ", len(ihsg), " rows\t")
        if len(ihsg) > 0:
            print(ihsg)
            ihsg = (
                ihsg.assign(
                    Kode="IHSG",
                    time_updated = datetime.datetime.now(),
                )
                .reset_index()
            )[["Date", "Kode", "Open", "High", "Low", "Close", "Volume", "time_updated"]]
            ihsg.to_sql("historical", if_exists="append", con=con, index=False)
            tickers = pd.read_sql(
            """
                SELECT DISTINCT Kode FROM historical
                WHERE Kode != "IHSG"
            """,
            con=con,
            ).iloc[:,0].to_list()
            for i in range(0, len(tickers), 50):
                ticker = [f"{kode}.JK" for kode in tickers[i : i + 50]]
                df = (
                    yfi.download(ticker, start=start_date, end=end_date, progress=False)
                    .T.unstack(level=1)
                    .T.reset_index()
                    .dropna()
                    .rename(columns={"level_1": "Kode"})
                )[["Date", "Kode", "Open", "High", "Low", "Close", "Volume"]]
                df["Kode"] = df["Kode"].str.replace(".JK", "")
                df = df.assign(time_updated = datetime.datetime.now())
                df.to_sql("historical", if_exists="append", con=con, index=False)


            # update patterns database
            tickers = ["IHSG"] + tickers
            start = time.time()
            for i, kode in enumerate(tickers):
                print(f"Finding Patterns for {kode} #{i+1}\t\t time elapsed = {time.time() - start:.2f} s")
                try:
                    search_result = find_patterns(df=pd.read_sql(f"""
                        SELECT * 
                        FROM historical 
                        WHERE Kode = '{kode}' 
                        ORDER BY Date
                    """,
                    con=con,
                    ))
                    if i == 0:
                        search_result.to_sql("patterns", if_exists="replace", con=con, index=False)
                    else:
                        search_result.to_sql("patterns", if_exists="append", con=con, index=False)
                except:
                    pass