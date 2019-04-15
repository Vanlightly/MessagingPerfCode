import os


def get_args(args):
    args_dict = dict()
    index = 1
    while index < len(args):
        key = args[index]
        value = args[index+1]
        args_dict[key] = value
        index += 2
        
    return args_dict

def get_mandatory_arg(args_dict, key):
    if key in args_dict:
        return args_dict[key]
    else:
        env_var = os.environ.get(key.replace("--", "").upper())
        if env_var is None:
            print(f"Missing mandatory argument {key}")
            exit(1)

        return env_var

def get_optional_arg(args_dict, key, default_value):
    if key in args_dict:
        return args_dict[key]
    else:
        env_var = os.environ.get(key.replace("--", "").upper())
        if env_var is None:
            return default_value
        else:
            return env_var

def is_true(val):
    if val.upper() == "TRUE":
        return True
    elif val.upper() == "FALSE":
        return False
    else:
        raise ValueError("Must be a boolean value")

def as_list(val):
    return val.split()