from os import environ


def override_environment(**envs):
    # Handy decorator, similar to override settings that will temporarily set environment
    # variables for a test, and then revert the values afterwards
    def decorator(func):
        def wrapped(*args, **kwargs):
            # Store the current environment variable values, and set new values
            curr_vals = {}
            for key, val in envs.items():
                curr_vals[key] = environ.get(key)

                # Force the given value to a string
                if type(val) == list:
                    environ[key] = ",".join(val)
                else:
                    environ[key] = "{}".format(val)

            # Run the wrapped function/method with it's args.kwargs
            try:
                func(*args, **kwargs)
            finally:
                # Restore environment variables to original values
                for key, val in curr_vals.items():
                    if val is None:
                        del environ[key]
                    else:
                        environ[key] = val

        return wrapped
    return decorator
