DROP TABLE IF EXISTS measurements;

CREATE TABLE measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    pre_transmission_up INTEGER NOT NULL,
    pre_transmission_down INTEGER NOT NULL,
    post_transmission_up INTEGER NOT NULL,
    post_transmission_down INTEGER NOT NULL,
    speedtest_up INTEGER NOT NULL,
    speedtest_down INTEGER NOT NULL,
    fast_up INTEGER NOT NULL,
    fast_down INTEGER NOT NULL,
    speedtest_ping INTEGER NOT NULL,
    fast_ping INTEGER NOT NULL
);
