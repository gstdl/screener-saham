from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, Arrow, NormalHead
from bokeh.palettes import Spectral4
from bokeh.embed import components
import sqlite3
import pandas as pd


def get_tickers(pattern, last_dates=1):
    # connect to database
    with sqlite3.connect("dataset/ihsg.db") as con:

        # retrieve data from database
        tickers = pd.read_sql(f"""
            SELECT Kode 
            FROM patterns
            WHERE Date IN (
                SELECT Date 
                FROM (
                    SELECT Date, ROW_NUMBER() OVER(ORDER BY Date DESC) AS rnk
                    FROM historical
                    WHERE Kode = 'IHSG'
                ) a 
                WHERE rnk <= {last_dates + 1}
            )
            AND Pattern = '{pattern}'
            ORDER BY Pattern_Score DESC, Open_Close_Change DESC, High_Low_Change DESC
        """,
        con=con,
        ).iloc[:, 0].to_list()

    return tickers

def get_data(kode, pattern):

    # connect to database
    with sqlite3.connect("dataset/ihsg.db") as con:

        # retrieve data from database
        df = pd.read_sql(f"""
            SELECT *
            FROM historical
            WHERE Kode = '{kode}'
            ORDER BY Date
        """, 
        con=con, 
        parse_dates=['Date'],
        )
        
        # df = pd.read_sql(f"""
        #     SELECT 
        #         historical.Date,
        #         historical.Open,
        #         historical.High,
        #         historical.Low,
        #         historical.Close, 
        #         patterns.Pattern_Score
        #     FROM historical
        #     LEFT JOIN (
        #         SELECT Date, Kode, Pattern_Score
        #         FROM patterns
        #         WHERE Pattern = '{pattern}'
        #     ) AS patterns
        #     USING(Kode, Date)
        #     WHERE Kode = '{kode}'
        #     ORDER BY Date
        # """, 
        # con=con, 
        # parse_dates=['Date'],
        # )

        nama = pd.read_sql(
            f"SELECT Nama FROM list_perusahaan WHERE Kode = '{kode}'", 
            con=con,
        ).values[0][0]

    return df, nama

def plot_candlestick(df, nama, kode):
    
    # calculate simple moving average
    for period in [5,20,200]:
        df[f'sma{period}'] = df['Close'].rolling(period, period).mean()
        
    # Prepare data for plotting
    cds = ColumnDataSource(df)
    cds_inc = ColumnDataSource(df[df["Close"] >= df["Open"]])
    cds_dec = ColumnDataSource(df[df["Open"] > df["Close"]])
    
    # assign figure canvas to variable p
    x_range = (max(len(df) - 60.5, 0), len(df))
    p = figure(
        tools="pan,zoom_in,zoom_out,box_zoom,undo,redo,reset,save", 
        plot_width=600, 
        plot_height=400,
        title = f"{kode}\t({nama})",
        x_range= x_range,
        y_range= (
            df.loc[x_range[0]//1-5:x_range[1], ["Open", "High", "Low", "Close", "sma5", "sma20", "sma200"]].min().min() * 0.875, 
            df.loc[x_range[0]//1-5:x_range[1], ["Open", "High", "Low", "Close", "sma5", "sma20", "sma200"]].max().max() * 1.125
        )
    )
    
    # xaxis setup
    p.xaxis.major_label_overrides = {
    i: date.strftime('%d %b %Y') for i, date in enumerate(df["Date"])
    }
    p.xaxis.bounds = (0, df.index[-1])
    p.xaxis.major_label_orientation = (22/7)/4
    p.grid.grid_line_alpha=0.3
    
    # # plot pattern arrow
    # for idx in df[df["Pattern_Score"].notna()].tail().index:
    #     row = df.loc[idx, ["Open", "High", "Low", "Close"]]
    #     x_start = row.min()
    #     if x_start < 200:
    #         x_start -= 2
    #         x_end = x_start - 4
    #     elif x_start < 500:
    #         x_start -= 4
    #         x_end = x_start - 4
    #     else:
    #         x_start -= 8
    #         x_end = x_start - 6
    #     p.add_layout(Arrow(
    #         end=NormalHead(fill_color="black"), 
    #         line_color="black",
    #         x_start = x_start,
    #         x_end = x_end,
    #         y_start = idx,
    #         y_end=idx
    #     ))
        

    # plot candlestick wicks with HoverTool
    p.add_tools(HoverTool(
        renderers=[p.segment("index", "High", "index", "Low", source=cds, color="black", line_width=1)],
        tooltips=[
            ("Date","@Date{%F}"),
            ("Open","@Open{0.2f}"),
            ("High", "@High{0.2f}"),
            ("Low", "@Low{0.2f}"),
            ("Close", "@Close{0.2f}"),
        ],
        formatters={"@Date":"datetime"}
    ))

    # plot candlestick bars
    for data, color in [(cds_inc, "#26a69a"), (cds_dec, "#ef5350")]:
        p.vbar("index", 0.5, "Open", "Close", source=data, fill_color=color, line_color="black", line_width=1)
    
    # plot moving average with HoverTool
    for period, color in zip([5,20,200], Spectral4):
        p.add_tools(HoverTool(
            renderers=[p.line(
                "index", 
                f"sma{period}", 
                source=cds, 
                line_width=2, 
                alpha=0.8, 
                color=color, 
                legend_label=f'SMA {period}\t')],
            tooltips=[
                (f"SMA {period}", "@sma%s{0.2f}" %(period)),
            ],
        ))
    
    # legend setup
    p.legend.location = "top_left"
    p.legend.click_policy="hide"
    p.legend.orientation="horizontal"
    
    # generate script and div
    script, div = components(p)

    return script, div