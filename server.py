import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import math

st.set_page_config(
    page_title="Stint Calculation",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title('Stint Calculation')

strats = st.sidebar.multiselect('Strats to simulate', ['avoid_low_tire', 'minimize_low_tire', 'least_stops'], [
                                'avoid_low_tire', 'minimize_low_tire', 'least_stops'], help='The possible strategies:\nEither avoid at any cost that you have to drive in low tires.\nTo stop in the round where you have to low tires - finishing the current round.\nNot to watch for tires at all and just stop when fuel is needed.')


__tires_perc_problem__ = .30
__fuel_amount_start__ = 100
__tire_change_sec__ = 3
__l_per_sec__ = 5

st.sidebar.write(
    f"Percentage at which tires get worse {__tires_perc_problem__ * 100}%")
st.sidebar.write(
    f"With how much litres of fuel do you start: {__fuel_amount_start__}l")
st.sidebar.write(f"How long does a tire stop take: {__tire_change_sec__}sec")
st.sidebar.write(f"Litres of found refueled per second: {__l_per_sec__}l")

overall_rounds = st.slider(
    "How many rounds do you drive:", 0, 100, 60, help='How many rounds the race has')

tire_per_round = st.slider(
    "How many percent of tire loss do you have per round:", 0, 40, 12, help='How many percent your tires decrease in a single race pace round')
fuel_per_round = st.slider(
    "How many litres of fuel do you need per round", 0, 40, 10, help='How many litres of fuel do you need in a single race pace round')

round_duration_sec = st.slider(
    "How long does a round on good tires take [sec]", 0, 300, 51, help='Expected round duration in race pace')
pit_stop_delta_time = st.slider(
    "How much seconds are lost if you pit:", 0, 60, 20, help='The time from entering the pit lane until leaving it, in comparison if you drive the normal way')


secs_lost_with_tires_low_per_round = st.slider(
    "How much are you losing if you are driving on low tires [sec per round]", 0, 40, 3, help='In seconds, how much slower you can drive if you have bad tires (< 30 %)')

fuel_safety = st.number_input(
    "How much extra fuel to calculate for the last stint:", 1, 20, 4, help='How many litres of fuel should we safe calculate to have over at the end for unexpected reasons, e.g. sudden rain stop')

rounds_fuel = math.floor(100 / fuel_per_round)
rounds_tires = math.floor(100 / tire_per_round)


def getTireLoss(tire_percent):
    # calculate how much rounds have been driven with low tires and multiply by the seconds lost by round

    rounds_with_low_tire = (max(0, 30 - tire_percent) / tire_per_round)

    return rounds_with_low_tire * secs_lost_with_tires_low_per_round, rounds_with_low_tire


def getFuelToRefuel(rounds_left, fuel_per_round, fuel_safety, current_fuel_percent):

    fuel_needed_to_finish = (rounds_left * fuel_per_round) + fuel_safety
    # either 100 percent or simply for how many rounds are left
    fuel_to_refuel = min(fuel_needed_to_finish, 100)
    # if we now need less, dont lower the val...
    return max(fuel_to_refuel, current_fuel_percent)


def doPitStop(fuel_percent, tire_percent, last_stop_round, df, reason):

    # print(f"PITSPOT in round: {current_round} (last stop in: {last_stop_round}) due to __{reason}__")

    rounds_left = (overall_rounds) - current_round
    fuel_calculated = getFuelToRefuel(
        rounds_left, fuel_per_round, fuel_safety, fuel_percent)

    # it starts with 30% so 30 - current tire = 30 - 25 = 5%, 12% per round = 40%, so 40%
    sec_lost_with_low_tire, rounds_with_low_tire = getTireLoss(tire_percent)

    df.append(dict(Task=f"Stint {len(df) + 1}", start=last_stop_round, finish=current_round, current_fuel=fuel_percent, current_tire=tire_percent,
              refueling_to=fuel_calculated, sec_lost_with_low_tire=sec_lost_with_low_tire, rounds_with_low_tire=rounds_with_low_tire, fueled_time=(fuel_calculated - fuel_percent) / __l_per_sec__))

    fuel_percent = fuel_calculated
    tire_percent = 100

    return fuel_percent, tire_percent, current_round


def makePlot(df):
    plotDf = pd.DataFrame(df)

    plotDf['days_start_to_end'] = plotDf.finish - plotDf.start

    cmap = plt.cm.coolwarm
    fig, ax = plt.subplots(1, figsize=(16, 6))
    ax.barh(plotDf.Task, plotDf.days_start_to_end, left=plotDf.start)

    plt.axvline(x=overall_rounds, color=cmap(1.), linestyle='--')

    for i, elem in enumerate(df):

        finish_round = elem.get('finish')
        rounds_with_low_tire = elem.get('rounds_with_low_tire')
        current_fuel = elem.get('current_fuel')

        if current_fuel <= 5:

            """
            4l fuel left
            we show it with < 5l
            l per round = 10
            5-4 = 1 / 10 = 0.1 rounds
            """

            plt.axvline(x=finish_round - ((5 - current_fuel) / fuel_per_round),
                        color=cmap(.5), linestyle='--')

        if rounds_with_low_tire > 0:
            plt.axvline(x=finish_round -
                        rounds_with_low_tire, color=cmap(0.), linestyle='--')

    custom_lines = [Line2D([0], [0], color=cmap(0.), linestyle='--'),
                    Line2D([0], [0], color=cmap(.5), linestyle='--'),
                    Line2D([0], [0], color=cmap(1.), linestyle='--')]

    ax.legend(custom_lines, ['Low tires', 'Fuel <= 5l', 'Finish Line'])
    # plt.show()
    st.pyplot(plt)


def prettyPrintDuration(seconds):
    if seconds > 60:
        return f"{int(seconds / 60)}m {int(seconds % 60)}s"
    else:
        return f"{int(seconds)}s"


splits = []

for i, strat in enumerate(strats):

    df = []

    current_round = 1
    fuel_percent = 100
    tire_percent = 100
    last_stop_round = 1

    st.header(f"Simulating with strat: {strat}")

    while current_round <= overall_rounds:

        fuel_percent -= fuel_per_round
        tire_percent -= tire_per_round

        # print(f"End of round: {current_round} - fuel: {fuel_percent}/ tire: {tire_percent}")

        # No pitstops in last round
        if current_round < overall_rounds:
            if fuel_percent < fuel_per_round:
                fuel_percent, tire_percent, last_stop_round = doPitStop(
                    fuel_percent, tire_percent, last_stop_round, df, 'FUEL')

            if strat == 'avoid_low_tire':
                # cant do another round without getting into red zone
                if tire_percent < (__tires_perc_problem__) * 100 + tire_per_round:
                    fuel_percent, tire_percent, last_stop_round = doPitStop(
                        fuel_percent, tire_percent, last_stop_round, df, 'TIRE')
            elif strat == 'minimize_low_tire':
                # this round with red tires will be done, then pitted
                if tire_percent < (__tires_perc_problem__) * 100:
                    fuel_percent, tire_percent, last_stop_round = doPitStop(
                        fuel_percent, tire_percent, last_stop_round, df, 'TIRE')
            elif strat == 'least_stops':
                # This is the last round which can be done before tires breaking
                if tire_percent < tire_per_round * 1:
                    fuel_percent, tire_percent, last_stop_round = doPitStop(
                        fuel_percent, tire_percent, last_stop_round, df, 'TIRE')
        elif current_round == overall_rounds:
            st.subheader("Summary")

            sec_lost_with_low_tire, rounds_with_low_tire = getTireLoss(
                tire_percent)

            # TODO add here the new fields added in the pitstop func
            df.append(dict(Task=f"Stint {len(df) + 1}", start=last_stop_round, finish=current_round, current_fuel=fuel_percent,
                      current_tire=tire_percent, refueling_to=fuel_percent, sec_lost_with_low_tire=sec_lost_with_low_tire, rounds_with_low_tire=rounds_with_low_tire, fueled_time=(fuel_percent - fuel_percent) / __l_per_sec__))

            for i, stint in enumerate(df):

                cur_fuel = stint.get('current_fuel')
                fuel_to = stint.get('refueling_to')
                cur_tire = stint.get('current_tire')

                if i + 1 == len(df):
                    st.write(
                        f"Finishing race with tire: {cur_tire}% and fuel: {cur_fuel}l")
                elif i + 2 == len(df):
                    st.write(
                        f"{i+1}. stop in round {stint.get('finish')} with tire: {cur_tire}% and fuel: {cur_fuel}l / refuel to: {fuel_to}l | with 1 overlap: {fuel_to - 1 * fuel_per_round}l | with 2 overlaps: {fuel_to - 2 * fuel_per_round}l")
                else:
                    st.write(
                        f"{i+1}. stop in round {stint.get('finish')} with tire: {cur_tire}% and fuel: {cur_fuel}l / refuel to: {fuel_to}l")

            racing_time = overall_rounds * round_duration_sec
            pitstop_time = len(df) * pit_stop_delta_time
            low_tire_loss = sum(
                [elem.get('sec_lost_with_low_tire') for elem in df])
            fuel_time_loss = sum(
                [elem.get('fueled_time') for elem in df])

            st.text('')
            st.text('')
            st.subheader('Race duration:')
            st.text(
                f"{overall_rounds} rounds = {prettyPrintDuration(racing_time)}")
            st.text(
                f"{len(df)} pitstops = {prettyPrintDuration(pitstop_time)} + fuel time: {prettyPrintDuration(fuel_time_loss)}")
            st.text(
                f"{prettyPrintDuration(low_tire_loss)} lost due to low tire.")

            st.text(
                f"Overall duration: {prettyPrintDuration(racing_time + pitstop_time + low_tire_loss + fuel_time_loss)}")

            # print(df)

            makePlot(df)

        current_round += 1
