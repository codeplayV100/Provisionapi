

from werkzeug.wrappers import Request,Response


def default(request):
    response = Response('Hello World!', mimetype='text/text')
    return response


def satish(request):
    response = Response('{"satish":"yerramsetti"}', mimetype='type/json')
    return response


def accounts(request):
    response = Response('{"account": "satishy"}',mimetype='type/json')
    return Response


def jobs(request):
    pass


def arrays(request):
    pass

