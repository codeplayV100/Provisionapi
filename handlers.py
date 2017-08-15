

from werkzeug.wrappers import Request,Response


def accounts(request):
    print request.url
    if request.method =="GET":
        default = "satish"
        print request.environ
        if request.environ.get("shortid",None) !=None:
            default = request.environ["shortid"]
        response = Response('{"account": %s}'%(default),mimetype='text/json')
        return response
    if request.method == "POST":
        response = Response('{"status": "Not implemented"}',mimetype='text/json')
        return response


def jobs(request):
    pass


def arrays(request):
    pass

