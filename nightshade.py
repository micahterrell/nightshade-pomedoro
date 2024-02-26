# License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>
# This is free software: you are free to change and redistribute it.
# There is NO WARRANTY, to the extent permitted by law.
# Written by Micah Terrell with support from his (lazy) cat Lucy

import os
import signal
import sys
import argparse
import time
import datetime

# Required before pygame imports to prevent pygame from spitting out a version message. :(
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide" 
from pygame import mixer

### Constants ###
CANONICAL_NAME = "Nightshade Pomedoro"
VERSION = "1.0"
DISCLAIMER = "License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>\n" \
            "This is free software: you are free to change and redistribute it.\n" \
            "There is NO WARRANTY, to the extent permitted by law."
SIGNATURE = "Written by Micah Terrell with support from his (lazy) cat Lucy"

PROGRAM_DESCRIPTION = "A simple pomedoro timer that logs completed work to a csv"
VERSION_HELP_MESSAGE = "Prints program version and other metadata"
TOPIC_HELP_MESSAGE = "The name of the work to be done. Time completed will be stored under this topic name in the log file | defaults to: %(default)s"
SCHEDULE_HELP_MESSAGE = "Configures the timing of pomedoro work and break periods. This takes the form:  work_minutes,break_minutes  where work_minutes and break_minutes are integers| defaults to: %(default)s"
OUTPUT_HELP_MESSAGE = "The path to write logged work segments to. NOTE: this blindly appends to the file if it already exists. The log file is formatted as a csv" \
        "(without a header) with each line taking the form: TOPIC,COMPLETED_WORK_SECONDS,COMPLETED_REST_SECONDS,UTC_COMPLETED_AT | defaults to: %(default)s"
ALARM_HELP_MESSAGE = "The path to the sound to play when a work/rest segment starts/ends. Supports file types accepted by pygame.mixer.Sound (WAV, MP3, or OGG) | defaults to: %(default)s"

def log_file(output_path):
    # setup our log file, creating a new one if it does not exist
    log_file = open(output_path, "a+", buffering=1)

    def write(topic, work_seconds, rest_seconds):
        log_file.write(f"{args.topic},{work_seconds},{rest_seconds},{datetime.datetime.now(datetime.timezone.utc)}\n")

    def close():
        log_file.close()

    return (write, close)

if __name__ == "__main__":
    # Parse provided arguments
    arg_parser = argparse.ArgumentParser(description='A foo that bars')
    #NOTE: -h and --help are elegantly handled by argparse
    arg_parser.add_argument("-v", "--version", action="store_true", help=VERSION_HELP_MESSAGE)
    arg_parser.add_argument("-t", "--topic", default="Work", help=TOPIC_HELP_MESSAGE)
    arg_parser.add_argument("-s", "--schedule", default="25,5", help=SCHEDULE_HELP_MESSAGE)
    arg_parser.add_argument("-o", "--output-path", default="pomedoro_times.csv", help=OUTPUT_HELP_MESSAGE)
    arg_parser.add_argument("-a", "--alarm-path", default="ship-bell.mp3", help=ALARM_HELP_MESSAGE)

    args = arg_parser.parse_args()
    if(args.version):
        print(f"{CANONICAL_NAME} {VERSION}")
        print(DISCLAIMER)
        print(SIGNATURE)
        quit()

    #check the format of the --schedule argument
    try:
        WORK_MINUTES, REST_MINUTES = str(args.schedule).strip().split(",")
        WORK_MINUTES = int(WORK_MINUTES)
        REST_MINUTES = int(REST_MINUTES)
        WORK_SECONDS = WORK_MINUTES * 60
        REST_SECONDS = REST_MINUTES * 60
    except:
        raise Exception(f"Invalid --schedule argument: {args.schedule}.")

    # Set up our Start and End bell sound
    mixer.init()
    alarm_sound = mixer.Sound(args.alarm_path)

    # init log file closure
    write_log, close_log = log_file(args.output_path)

    # loop variables
    is_work_period = True
    is_rest_period = False
    cycles_finished = 0 # a cycle is a combo of 1 work interval and 1 rest interval.
    end_time = 0
    current_time = 0
    
    # handle sigint so we can write the final log before exiting
    def sigint_handler(_s, _f):
        print('\nSIGINT received, writing final log...')
        time_remaining = int(end_time - current_time)
        if(is_work_period):
            write_log(args.topic, WORK_SECONDS - time_remaining, 0)
        elif(is_rest_period):
            write_log(args.topic, WORK_SECONDS, REST_SECONDS - time_remaining)
        close_log()
        sys.exit(0)
    signal.signal(signal.SIGINT, sigint_handler)

    # Execute until user halts
    while(True):
        ### Start the work period
        alarm_sound.play()
        print(f"Working on: {args.topic} | Cycle #:{cycles_finished + 1}")

        is_work_period = True
        end_time = int(time.time() + WORK_SECONDS)
        current_time = time.time()

        # Loop until the work cycle is over
        while(current_time <= end_time):
            seconds_left = int(end_time - current_time)
            print("\r", end="")
            print(f"Work Period | Remaining Time: {datetime.timedelta(seconds=seconds_left)}", end="")
            sys.stdout.flush()
            time.sleep(1)
            current_time = int(time.time())

        print("\rWork Period Complete                                     ")
        sys.stdout.flush()
        alarm_sound.play()
        time.sleep(1)

        ### Start the rest period
        print(f"Starting rest cycle {cycles_finished + 1}")
        
        is_work_period = False
        is_rest_period = True
        end_time = int(time.time() + REST_SECONDS)
        current_time = time.time()

        # Loop until the rest cycle is over
        while(current_time <= end_time):
            seconds_left = int(end_time - current_time)
            print("\r", end="")
            print(f"Rest Period | Remaining Time: {datetime.timedelta(seconds=seconds_left)}", end="")
            sys.stdout.flush()
            time.sleep(1)
            current_time = int(time.time())
        is_rest_period = False
        print("\rRest Timer Expired                                ")
        sys.stdout.flush()
        alarm_sound.play()
        time.sleep(1)

        #Log the completed cycle
        write_log(args.topic, WORK_MINUTES * 60, REST_MINUTES * 60)

        input("Press ENTER to start the next cycle")
        cycles_finished += 1
