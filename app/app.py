from flask import Flask, render_template, request
from helper_script import get_tickers, get_data, plot_candlestick
from update_database import update_database, get_last_update_time
from bokeh.resources import INLINE
import json

app = Flask(__name__)

# load patterns file
with open("dataset/patterns.json") as f:
    patterns = json.load(f)
# sort `patterns` by value
patterns = dict(sorted(patterns.items(), key=lambda item: item[1]))

last_update_time = get_last_update_time()

@app.route("/", methods=["GET", "POST"])
def home():
    global last_update_time
    pattern = request.args.get("pattern", None)
    if request.method == "POST":
        update_database()
        last_update_time = get_last_update_time()
        return render_template("index.html", patterns=patterns, selected=pattern, last_update_time=last_update_time)
    if pattern:
        return plot(pattern)
    else:
        return render_template("index.html", patterns=patterns, selected=False, last_update_time=last_update_time)


def plot(pattern):
    print(pattern)
    plot_divs, plot_scripts = [], []
    tickers = get_tickers(patterns[pattern])
    print(len(tickers))
    if len(tickers) == 0:
        return render_template("no_pattern_found.html", patterns=patterns, selected=pattern)
    else:
        for i, kode in enumerate(tickers):
            print(f"{kode}\t\t {i}/{len(tickers)}")
            df, nama = get_data(kode, patterns[pattern])
            if len(df[["Open", "High", "Low", "Close"]].tail(3).drop_duplicates(keep=False)) > 0:
                plot_script, plot_div = plot_candlestick(df, nama, kode)
                plot_scripts.append(plot_script)
                plot_divs.append(plot_div)
        return render_template(
            "plot.html", 
            patterns=patterns, 
            selected=pattern,
            js_resources = INLINE.render_js(),
            css_resources = INLINE.render_css(),
            plot_divs = plot_divs, 
            plot_scripts = plot_scripts,
            last_update_time=last_update_time
        )

    
if __name__ == "__main__":
    app.run(debug=True) 