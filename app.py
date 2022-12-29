import shutil
import sys
import logging

import flask
from flask import Flask, Response
from fritzconnection.lib.fritzstatus import FritzStatus as FS
import speedtest
import os
from time import sleep
import sqlite3
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
import pandas
import plotly.graph_objects as go
import json
import plotly
import datetime
import fast


app = Flask(__name__)
SOLD_NUMBER = 400_000_000
TARGET_DOWNLOAD = 0.5
TARGET_UPLOAD = 0.25



def redo_schema():
    connection = sqlite3.connect('log.db')
    with open("schema.sql") as schema:
        connection.executescript(schema.read())
    connection.commit()
    connection.close()

def init_db():
    connection = sqlite3.connect('log.db')

    cursor = connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='measurements';")
    rows = cursor.fetchall()
    cursor.close()
    app.logger.info(rows, file=sys.stderr)
    app.logger.info("test", file=sys.stderr)
    if not rows:
        redo_schema()
    connection.commit()
    connection.close()

def log_in_db(
    pre_transmission_up,
    pre_transmission_down,
    post_transmission_up,
    post_transmission_down,
    speedtest_up,
    speedtest_down,
    speedtest_ping,
    fast_up,
    fast_down,
    fast_ping):
    connection = sqlite3.connect('log.db')


    cursor = connection.cursor()
    cursor.execute(f"INSERT INTO measurements"
                   f"("
                   f"pre_transmission_up,"
                   f"pre_transmission_down,"
                   f"post_transmission_up,"
                   f"post_transmission_down,"
                   f"speedtest_up,"
                   f"speedtest_down,"
                   f"speedtest_ping,"
                   f"fast_up,"
                   f"fast_down,"
                   f"fast_ping"
                   f") VALUES ("
                   f"{pre_transmission_up},"
                   f"{pre_transmission_down},"
                   f"{post_transmission_up},"
                   f"{post_transmission_down},"
                   f"{speedtest_up},"
                   f"{speedtest_down},"
                   f"{speedtest_ping},"
                   f"{fast_up},"
                   f"{fast_down},"
                   f"{fast_ping}"
                   f");")
    connection.commit()
    connection.close()


def create_download_figure(dataframe):
    fig = go.Figure()
    times = dataframe["created"]
    sold_line = dataframe["id"] * 0 + (SOLD_NUMBER * 1)
    target_line = dataframe["id"] * 0 + (SOLD_NUMBER * TARGET_DOWNLOAD)

    max_fritz = dataframe[["pre_transmission_down", "post_transmission_down"]].max(axis=1)
    fig.add_trace(go.Scatter(x=times,
                             y=dataframe["fast_down"] + max_fritz,
                             name="Adjusted Netflix",
                             ),
                  )

    fig.add_trace(go.Scatter(x=times,
                             y=target_line,
                             name="gesetzlich notwendige Leistung",
                             fill='tonexty',
                             )
                  )

    fig.add_trace(go.Scatter(x=times,
                             y=dataframe["speedtest_down"] + max_fritz,
                             name="Adjusted OOkla",
                             fill='tonexty',
                             ),
                  )

    fig.add_trace(go.Scatter(x=times,
                             y=sold_line,
                             name="versprochene Leistung",
                             )
                  )

    fig.add_trace(go.Scatter(x=times,
                             y=max_fritz,
                             name="fritzbox Download used",
                             fill="tozeroy"))

    return fig

def create_upload_figure(dataframe):
    fig = go.Figure()
    times = dataframe["created"]
    sold_line = dataframe["id"] * 0 + (SOLD_NUMBER * .5)
    target_line = dataframe["id"] * 0 + (SOLD_NUMBER * TARGET_UPLOAD)

    max_fritz = dataframe[["pre_transmission_down", "post_transmission_down"]].max(axis=1)
    fig.add_trace(go.Scatter(x=times,
                             y=dataframe["fast_up"] + max_fritz,
                             name="Adjusted Netflix",
                             ),
                  )

    fig.add_trace(go.Scatter(x=times,
                             y=target_line,
                             name="gesetzlich notwendige Leistung",
                             fill='tonexty'
                             )
                  )

    fig.add_trace(go.Scatter(x=times,
                             y=dataframe["speedtest_up"] + max_fritz,
                             name="Adjusted OOkla",
                             fill='tonexty',
                             ),
                  )

    fig.add_trace(go.Scatter(x=times,
                             y=sold_line,
                             name="versprochene Leistung",
                             )
                  )

    fig.add_trace(go.Scatter(x=times,
                             y=max_fritz,
                             fill='tozeroy',
                             name="fritzbox Upload used",))

    return fig


@app.route('/')
def hello_world():
    #return 'Hello World!'
    init_db()
    connection = sqlite3.connect('log.db')
    dataframe = pandas.read_sql_query("SELECT * FROM measurements;", connection, parse_dates="created")
    connection.close()

    fig = create_download_figure(dataframe)
    downloadJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    upfig = create_upload_figure(dataframe)
    uploadJSON = json.dumps(upfig, cls=plotly.utils.PlotlyJSONEncoder)
    total_measurements, bad_download, bad_upload = get_measurements(dataframe, None)
    total_measurements_weekly, bad_download_weekly, bad_upload_weekly = get_measurements(dataframe, datetime.timedelta(weeks=1))
    total_measurements_monthly, bad_download_monthly, bad_upload_monthly = get_measurements(dataframe, datetime.timedelta(days=30))

    return flask.render_template('notdash.html',
                                 downloadJSON=downloadJSON,
                                 uploadJSON=uploadJSON,
                                 total_measurements=total_measurements,
                                 bad_download=bad_download,
                                 bad_upload=bad_upload,
                                 total_measurements_monthly=total_measurements_monthly,
                                 bad_download_monthly=bad_download_monthly,
                                 bad_upload_monthly=bad_upload_monthly,
                                 total_measurements_weekly=total_measurements_weekly,
                                 bad_download_weekly=bad_download_weekly,
                                 bad_upload_weekly=bad_upload_weekly,
                                 )

def get_measurements(dataframe_raw, timedelta):
    if timedelta is None:
        dataframe = dataframe_raw
    else:
        target_date = datetime.datetime.now()
        target_date -= timedelta
        dataframe = dataframe_raw[dataframe_raw["created"] >= target_date]
    total = len(dataframe)
    bad_download = len(dataframe[dataframe[["speedtest_down", "fast_down"]].max(axis=1) + dataframe[["pre_transmission_down", "post_transmission_down"]].max(axis=1) < SOLD_NUMBER * TARGET_DOWNLOAD])
    bad_upload = len(dataframe[dataframe[["speedtest_up", "fast_up"]].max(axis=1) + dataframe[["pre_transmission_up", "post_transmission_up"]].max(axis=1) < SOLD_NUMBER * TARGET_UPLOAD])
    return total, bad_download, bad_upload




@app.route('/force_measurement')
def force_measurement():
    perform_test_and_store()
    return hello_world()

@app.route('/get_csv')
def get_csv():
    init_db()
    connection = sqlite3.connect('log.db')
    dataframe = pandas.read_sql_query("SELECT * FROM measurements;", connection)
    connection.close()
    return Response(
        dataframe.to_csv(),
        mimetype="text/csv",
        headers={"Content-disposition":
                     "attachment; filename=Download_Messdaten.csv"})


def get_ookla_result_dict():
    s = speedtest.Speedtest()
    s.get_servers([])
    s.get_best_server()
    s.download()
    s.upload()
    return s.results.dict()

def getFritzBoxCurrentDataRate():
    fs = FS(address="fritz.box")
    return fs.transmission_rate

def perform_test_and_store():
    init_db()
    pre_up, pre_down = getFritzBoxCurrentDataRate()
    speedtest_dict = get_ookla_result_dict()
    sleep(5)
    fast_dict = fast.measure()
    sleep(1)
    getFritzBoxCurrentDataRate()
    sleep(1)
    getFritzBoxCurrentDataRate()
    sleep(1)
    getFritzBoxCurrentDataRate()
    sleep(1)
    getFritzBoxCurrentDataRate()
    sleep(1)
    getFritzBoxCurrentDataRate()
    sleep(1)
    post_up, post_down = getFritzBoxCurrentDataRate()

    test_up = speedtest_dict["upload"]
    test_down = speedtest_dict["download"]
    fast_up = fast_dict["upload_bitrate"]
    fast_down = fast_dict["download_bitrate"]
    fast_ping = fast_dict["latency"]
    speedtest_ping = speedtest_dict["ping"]
    log_in_db(pre_transmission_up=pre_up,
              post_transmission_up=post_up,
              pre_transmission_down=pre_down,
              post_transmission_down=post_down,
              speedtest_up=test_up,
              speedtest_down=test_down,
              speedtest_ping=speedtest_ping,
              fast_up=fast_up,
              fast_down=fast_down,
              fast_ping=fast_ping,
              )
    free_space = shutil.disk_usage(".")
    app.logger.info(f"{free_space}")


if __name__ == '__main__':
    app.run(debug=True)

if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    app.logger.info("scheduler initialized")
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=perform_test_and_store, trigger="interval", seconds=3600)
    scheduler.start()
else:
    app.logger.warning("scheduler skipped")

atexit.register(lambda: scheduler.shutdown())
