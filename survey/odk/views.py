from datetime import datetime
import pytz, os, base64
from functools import wraps
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render_to_response, get_object_or_404, render
from django.http import HttpResponse, HttpResponseBadRequest, \
    HttpResponseRedirect, HttpResponseForbidden, Http404, StreamingHttpResponse
from django.core.servers.basehttp import FileWrapper
from django.core.files.storage import get_storage_class
from django.contrib.auth.decorators import login_required, permission_required
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.template import RequestContext, loader
from survey.odk.utils.log import audit_log, Actions, logger
from survey.odk.utils.odk_helper import get_households, process_submission, disposition_ext_and_date, \
	response_with_mimetype_and_name, OpenRosaResponseBadRequest, \
    OpenRosaResponseNotAllowed, OpenRosaResponse, OpenRosaResponseNotFound,\
    BaseOpenRosaResponse, HttpResponseNotAuthorized, http_basic_investigator_auth
from survey.models import Survey, Investigator, Household
from django.utils.translation import ugettext as _
from django.contrib.sites.models import Site
from survey.utils.query_helper import get_filterset
from survey.models import ODKSubmission

def authenticate(request):
	return True

def get_survey_xform(household):
    survey = household.survey
    return render_to_string("odk/survey_form.xml", {
		'household': household,
		'survey' : household.survey,
		})

def base_url(request):
	return '%s://%s' % (request.META.get('wsgi.url_scheme'), request.META.get('HTTP_HOST')) #Site.objects.get_current().name;

@login_required
@permission_required('auth.can_view_aggregates')
def submission_list(request):
	odk_submissions = ODKSubmission.objects.all()
	search_fields = ['investigator__name', 'survey__name', 'household__uid', 'form_id', 'instance_id']
	if request.GET.has_key('q'):
		odk_submissions = get_filterset(odk_submissions, request.GET['q'], search_fields)
	return render(request, 'odk/submission_list.html', { 'submissions' : odk_submissions,
                                                 'request': request})

@http_basic_investigator_auth
@require_GET
def form_list(request, username):
	"""
		This is where ODK Collect gets its download list.
	"""
	if authenticate(request):
		investigator = get_object_or_404(Investigator, mobile_number=username)
		#to do - Make fetching households more e
		households = get_households(investigator)
		audit = {}
		audit_log(Actions.USER_FORMLIST_REQUESTED, request.user, investigator,
			  _("Requested forms list. for %s" % username), audit, request)
		response = render_to_response("odk/xformsList.xml", {
		'households': households,
		'investigator' : investigator,
		'base_url' : base_url(request),
		}, mimetype="text/xml; charset=utf-8")
		response['X-OpenRosa-Version'] = '1.0'
		tz = pytz.timezone(settings.TIME_ZONE)
		dt = datetime.now(tz).strftime('%a, %d %b %Y %H:%M:%S %Z')
		response['Date'] = dt
		return response
	else:
		return HttpResponseNotAuthorized()

@http_basic_investigator_auth
def download_xform(request, username, household_id):
	if authenticate(request):
		investigator = get_object_or_404(Investigator, mobile_number=username)
		#to do - Make fetching households more e
		household = get_object_or_404(Household, uid=household_id, investigator=investigator)
		survey_xform = get_survey_xform(household)
		audit = {
		    "xform": household_id
		}
		audit_log( Actions.FORM_XML_DOWNLOADED, request.user, investigator, 
					_("Downloaded XML for form '%(id_string)s'.") % {
															"id_string": household_id
														}, audit, request)
		response = response_with_mimetype_and_name('xml', 'survey%s' %household_id,
		                                           show_date=False)
		response.content = survey_xform
		return response
	else:
		return HttpResponseNotAuthorized()

@http_basic_investigator_auth
@require_http_methods(["POST"])
@csrf_exempt
def submission(request, username=None):
	if authenticate(request):
		investigator = get_object_or_404(Investigator, mobile_number=username)
		context = RequestContext(request)
		submission_date = datetime.now().isoformat()
		xml_file_list = []
		html_response = False
		# request.FILES is a django.utils.datastructures.MultiValueDict
		# for each key we have a list of values
		try:
			xml_file_list = request.FILES.pop("xml_submission_file", [])
			if len(xml_file_list) != 1:
				return OpenRosaResponseBadRequest(
	                _(u"There should be a single XML submission file.")
	            	)
			media_files = request.FILES.values()
			submission_reports = process_submission(investigator, xml_file_list[0], 			media_files=media_files)
			logger.info(submission_reports)
			if len(submission_reports) == 0:
				return OpenRosaResponseBadRequest(
		            _(u"Seems there are no forms in your submission.")
		        )				
			submission_report = submission_reports[0]
			context.message = _(settings.ODK_SUBMISSION_SUCCESS_MSG)
			context.instanceID = u'uuid:%s' % submission_report.instance_id
			context.formid = submission_report.form_id
			context.submissionDate = submission_date
			context.markedAsCompleteDate = submission_date
			t = loader.get_template('odk/submission.xml')
			audit = {}
			audit_log( Actions.SUBMISSION_CREATED, request.user, investigator, 
					_("Downloaded XML for form '%(id_string)s'.") % {
															"id_string": submission_report.form_id
														}, audit, request)
			response = BaseOpenRosaResponse(t.render(context))
			response.status_code = 201
			response['Location'] = request.build_absolute_uri(request.path)
			return response
		except Exception:
			return OpenRosaResponseBadRequest(
                _(u"Error encoutered while processing your form.")
            )
	else:
		return HttpResponseNotAuthorized()

