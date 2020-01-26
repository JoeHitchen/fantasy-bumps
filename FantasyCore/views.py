from django.http import JsonResponse


healthcheck_notice = 'This healthcheck gives the name of the service and echos any GET data provided to demonstrate a dynamic response.'  # noqa: E501


def healthcheck(request):
    return JsonResponse({
        **request.GET.dict(),
        'name': 'FantasyBumps',
        'notice': healthcheck_notice,
    })

