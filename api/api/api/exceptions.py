
class BaseCustomException(Exception):
    status_code = None
    error_message = None
    is_an_error_response = True

    def __init__(self, error_message):
        Exception.__init__(self)
        self.error_message = error_message

    def to_dict(self):
        return {'error_message', self.error_message}

class MissingParametersException(BaseCustomException):
    status_code = 400

    def __init__(self, parameters):
        error_message = 'Missing parameters: ' + ', '.join(parameters)
        BaseCustomException.__init__(self, error_message)