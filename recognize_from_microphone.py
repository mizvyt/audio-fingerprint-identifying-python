#!/usr/bin/python3
import sys
import logging
import argparse
from argparse import RawTextHelpFormatter
from termcolor import colored

import libs.fingerprint as fingerprint
from libs.config import get_config
from libs.reader_microphone import MicrophoneReader
from libs.visualiser_console import VisualiserConsole as visual_peak
from libs.visualiser_plot import VisualiserPlot as visual_plot
from libs.db_sqlite import SqliteDatabase

# from libs.db_mongo import MongoDatabase
from libs.utils import find_matches, print_match_results


def run_recognition():
    config = get_config()

    # Set up logging
    handlers = []
    if bool(config["log.console_out"]):
        handlers.append(logging.StreamHandler())
    if bool(config["log.file_out"]):
        handlers.append(logging.FileHandler("microphone_rec.log"))

    logger = logging.basicConfig(
        handlers=handlers,
        format=config["log.format"],
        level=config["log.level"],
    )

    db = SqliteDatabase()

    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument("-s", "--seconds", nargs="?")
    args = parser.parse_args()

    if not args.seconds:
        parser.print_help()
        sys.exit(0)

    seconds = int(args.seconds)

    chunksize = 2 ** 12  # 4096
    channels = int(config["channels"])  # 1=mono, 2=stereo

    record_forever = False
    save_recorded = bool(config["mic.save_recorded"])
    visualise_console = bool(config["mic.visualise_console"])
    visualise_plot = bool(config["mic.visualise_plot"])

    reader = MicrophoneReader()

    reader.start_recording(
        seconds=seconds, chunksize=chunksize, channels=channels
    )

    msg = " * started recording.."
    logger.info(msg)
    # print(colored(msg, attrs=["dark"]))

    while True:
        bufferSize = int(reader.rate / reader.chunksize * seconds)

        for i in range(0, bufferSize):
            nums = reader.process_recording()

            if visualise_console:
                msg = colored("   %05d", attrs=["dark"]) + colored(
                    " %s", "green"
                )
                logger.info(msg, visual_peak.calc(nums))
                # print(msg % visual_peak.calc(nums))
            else:
                msg = "   processing %d of %d.." % (i, bufferSize)
                logger.info(msg)
                # print(colored(msg, attrs=["dark"]))

        if not record_forever:
            break

    if visualise_plot:
        data = reader.get_recorded_data()[0]
        visual_plot.show(data)

    reader.stop_recording()

    msg = " * recording has been stopped"
    logger.info(msg)
    # print(colored(msg, attrs=["dark"]))

    data = reader.get_recorded_data()

    msg = " * recorded %d samples"
    logger.info(msg, len(data[0]))
    # print(colored(msg, attrs=["dark"]) % len(data[0]))

    if save_recorded:
        reader.save_recorded("test.wav")

    Fs = fingerprint.DEFAULT_FS
    channel_amount = len(data)
    matches = []

    for channeln, channel in enumerate(data):
        msg = "   fingerprinting channel %d/%d"
        logger.info(msg, channeln + 1, channel_amount)
        # print(colored(msg, attrs=["dark"]) % (channeln + 1, channel_amount))

        matches.extend(find_matches(db, channel, logger, Fs))

        msg = "   finished channel %d/%d, got %d hashes"
        logger.info(msg, channeln + 1, channel_amount, len(matches))
        # print(
        #     colored(msg, attrs=["dark"])
        #     % (channeln + 1, channel_amount, len(matches))
        # )

    print_match_results(db, matches, logger)


if __name__ == "__main__":
    run_recognition()
