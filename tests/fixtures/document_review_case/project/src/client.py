TIMEOUT_SECONDS = 10


def send(operation):
    for attempt in range(2):
        if operation():
            return True
    return False
