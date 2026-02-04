import logging
import subprocess
import json
from math import sqrt, pow, pi



LOG_PADDING_INFO = 33
LOG_PADDING_WARNING = 36
LOG_PADDING_ERROR = 34
LOG_INDENTATION_STR = ".."


def shell_command(bin, *args, logging_indentation_level=0):
    arg_list = []
    arg_list.insert(0, str(bin))
    for arg in args:
        if arg:  # Prevents empty strings from being written into list
            arg_list.append(str(arg))

    args_for_logger = " ".join(arg_list)

    logging.info(f"{LOG_INDENTATION_STR*logging_indentation_level} Shell command: {args_for_logger}")

    try:
        process = subprocess.run( arg_list,
                                  stdout = subprocess.PIPE,
                                  stderr = subprocess.PIPE,
                                  check = True,
                                  universal_newlines = True )

        output = process.stdout + process.stderr

    except FileNotFoundError:
        logging.warning( f"Problems with shell command: {args_for_logger}\n"
                         f"{LOG_PADDING_WARNING}-> it appears your shell does not know this command." )

        logging.error("Shell command failed!", exc_info=True)
        raise

    except subprocess.CalledProcessError as e:
        output = e.stdout + e.stderr

        logging.warning( f"Problems with shell command: {args_for_logger}\n"
                         "{LOG_PADDING_WARNING}-> the output returned to the shell is:\n"
                         f"{output}" )

        logging.error("Shell command failed!", exc_info=True)
        raise

    logging.info( f"{LOG_INDENTATION_STR*(logging_indentation_level+1)} Output:\n"
                  f"{output}" )

    return output


def load_config(config_path):
    with open(config_path, "r") as file:
        config = json.load(file)

    return config


def convert_to_fortran_bool(boolean_value):
    return f".{str(boolean_value).upper()}."


def domain_label(domain_id):
    return f"DOM{domain_id:02d}"


def compute_resolution_from_rnbk(n, k):
    earth_radius = 6371.0
    return earth_radius * sqrt(pi / 5) / (n * pow(2, k))