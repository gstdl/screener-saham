import tabula
import yfinance as yfi
import sqlite3
import pandas as pd
import json
import talib
import time
import datetime
import warnings

warnings.filterwarnings("ignore")

with open("patterns.json", "r") as f:
    patterns = json.load(f)

# update_time = datetime.datetime.now()
# dummy update time
update_time = "2021-05-01 15:20:03.672744"

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
    result = result.assign(time_updated = update_time)
    return result


def pull_data_yfi():
    start = time.time()
    with sqlite3.connect("ihsg.db") as con:
        tickers = pd.read_sql(
        """
            SELECT Kode FROM list_perusahaan
            WHERE Kode != "IHSG"
        """,
        con=con,
        ).values.flatten()
        ihsg = (
            yfi.download("^JKSE", start="2015-01-01", end="2021-05-01", progress=False)
            .reset_index()
            .dropna()
            .assign(Kode="IHSG")
        )
        ihsg = ihsg[["Date", "Kode", "Open", "High", "Low", "Close", "Volume"]]
        ihsg = ihsg.assign(time_updated = update_time)
        ihsg.to_sql("historical", if_exists="replace", con=con, index=False)
        pattern_search = find_patterns(ihsg)
        pattern_search.to_sql("patterns", if_exists="replace", con=con, index=False)
        for i in range(0, len(tickers), 50):
            ticker = [f"{kode}.JK" for kode in tickers[i : i + 50]]
            df = (
                yfi.download(ticker, start="2015-01-01", end="2021-05-01", progress=False)
                .T.unstack(level=1)
                .T.reset_index()
                .dropna()
                .rename(columns={"level_1": "Kode"})
            )
            df = df[["Date", "Kode", "Open", "High", "Low", "Close", "Volume"]]
            df["Kode"] = df["Kode"].str.replace(".JK", "")
            for j, kode in enumerate(df["Kode"].unique()):
                print(f"Finding Patterns for {kode} #{i+j+1}\t\t time elapsed = {time.time() - start:.2f} s")
                pattern_search = find_patterns(df[df["Kode"] == kode])
                pattern_search.to_sql("patterns", if_exists="append", con=con, index=False)
            df = df.assign(time_updated = update_time)
            df.to_sql("historical", if_exists="append", con=con, index=False)

def pull_data_klasifikasi_industri():
    with sqlite3.connect("ihsg.db") as con:
        cur = con.cursor()
        cur.execute("DROP TABLE IF EXISTS list_perusahaan")
        cur.execute("""
            CREATE TABLE list_perusahaan (
                Kode VARCHAR(4), 
                Nama TEXT, 
                Sektor TEXT,
                Instrumen TEXT)
        """)
        cur.execute("""
            INSERT INTO list_perusahaan VALUES
            ('IHSG', 'Indeks Harga Saham Gabungan', NULL, 'Indeks')
        """)
        # TODO: Change Schema from Star Schema to Snowflake Schema
        # list_perusahaan table will be the dimension table for sector and sub-sector fact tables
        # note: list_perusahaan table is a dimension table for historical fact table
        
        dfs = tabula.read_pdf("Klasifikasi Industri Perusahaan Tercatat.pdf", pages="all", stream=True)
        # print(len(dfs))
        for df in dfs:
            kode, nama, sektor = None, None, None
            for row in df.iloc[2:,:].itertuples():
                if kode is not None and pd.notna(row[2]):
                    cur.execute(f"""
                        INSERT INTO list_perusahaan VALUES
                        ('{kode}', '{nama}', '{sektor}', 'Saham')
                    """)
                    kode, nama, sektor = None, None, None
                elif kode is not None and pd.isna(row[2]):
                    if pd.notna(row[3]):
                        nama += " " + row[3] 
                    if pd.notna(row[5]):
                        sektor += " " + row[5]
                if kode is None and nama is None and sektor is None and pd.notna(row[2]):
                    if "saham" in row[8].lower():
                        kode = row[2]
                        nama = row[3]
                        sektor = row[5]
            else:
                if kode is not None:
                    cur.execute(f"""
                        INSERT INTO list_perusahaan VALUES
                        ('{kode}', '{nama}', '{sektor}', 'Saham')
                    """)
            print("INSERTION RESULT: \n")
            print(pd.read_sql("SELECT * FROM list_perusahaan", con=con).tail(2))
            print(pd.read_sql("SELECT * FROM list_perusahaan", con=con).shape)
            print("\n\n*--\n")
        con.commit()

if __name__ == "__main__":
    pull_data_klasifikasi_industri()
    # pull_data_yfi()
