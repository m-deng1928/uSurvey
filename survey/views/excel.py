import csv
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from survey.forms.filters import SurveyBatchFilterForm
from survey.models import Survey, Interviewer
from survey.models import Batch, LocationType
from survey.services.results_download_service import ResultsDownloadService, ResultComposer
from survey.utils.views_helper import contains_key
from survey.tasks import email_task


def _process_export(survey_batch_filter_form):
    batch = survey_batch_filter_form.cleaned_data['batch']
    survey = survey_batch_filter_form.cleaned_data['survey']
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % (batch.name if batch else survey.name)
    data = ResultsDownloadService(batch=batch, survey=survey).generate_report()
    writer = csv.writer(response)
    for row in data:
        writer.writerow(row)
    return response

@login_required
@permission_required('auth.can_view_aggregates')
def download(request):
    survey_batch_filter_form = SurveyBatchFilterForm()
    if request.GET:
        survey_batch_filter_form = SurveyBatchFilterForm(request.GET)
        if survey_batch_filter_form.is_valid():
            if request.GET.get('action') == 'Email Spreadsheet':
                batch = survey_batch_filter_form.cleaned_data['batch']
                survey = survey_batch_filter_form.cleaned_data['survey']
                composer = ResultComposer(request.user, ResultsDownloadService(batch=batch, survey=survey))
                email_task.delay(composer)
                messages.warning(request, "Email would be sent to you shortly. This could take a while.")
            else:
                return _process_export(survey_batch_filter_form)
    return render(request, 'aggregates/download_excel.html', {'survey_batch_filter_form': survey_batch_filter_form})

@login_required
@permission_required('auth.can_view_aggregates')
def _list(request):
    surveys = Survey.objects.order_by('name')
    batches = Batch.objects.order_by('order')
    return render(request, 'aggregates/download_excel.html', {'batches': batches, 'surveys': surveys})

@login_required
@permission_required('auth.can_view_aggregates')
def completed_interviewer(request):
    batch = None
    survey = None
    params = request.POST
    if contains_key(params, 'survey'):
        survey = Survey.objects.get(id=params['survey'])
    if contains_key(params, 'batch'):
        batch = Batch.objects.get(id=params['batch'])
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="interviewer.csv"'
    header = ['Interviewer', 'Access Channels']
    header.extend(LocationType.objects.exclude(name__iexact='country').values_list('name', flat=True))
    data = [header]
    data.extend(survey.generate_completion_report(batch=batch))
    writer = csv.writer(response)
    for row in data:
        writer.writerow(row)
    return response

@permission_required('auth.can_view_aggregates')
def interviewer_report(request):
    surveys = Survey.objects.all()
    batches = Batch.objects.all()
    return render(request, 'aggregates/download_interviewer.html', {'surveys':surveys, 'batches': batches})
