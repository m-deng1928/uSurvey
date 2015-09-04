from datetime import date, timedelta
from django.conf import settings
from django.core.validators import MinLengthValidator, MaxLengthValidator, MinValueValidator, MaxValueValidator
from django.db import models
from survey.interviewer_configs import LEVEL_OF_EDUCATION, LANGUAGES, COUNTRY_PHONE_CODE, INTERVIEWER_MIN_AGE, INTERVIEWER_MAX_AGE
from survey.models.base import BaseModel
from survey.models.access_channels import USSDAccess, ODKAccess
from survey.models.locations import Location
import random
from django.core.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from survey.models.household_batch_completion import HouseSurveyCompletion, HouseholdBatchCompletion
from survey.models.households import Household

def validate_min_date_of_birth(value):
    if date.today() - relativedelta(years=INTERVIEWER_MIN_AGE) < value:
        raise ValidationError('interviewers must be at most %s years' % INTERVIEWER_MIN_AGE)

def validate_max_date_of_birth(value):
    if  date.today() - relativedelta(years=INTERVIEWER_MAX_AGE) > value:
        raise ValidationError('interviewers must not be at more than %s years' % INTERVIEWER_MAX_AGE)

class Interviewer(BaseModel):
    MALE = '1'
    FEMALE = '0'
    name = models.CharField(max_length=100, blank=False, null=False)
    gender = models.CharField(default=MALE, verbose_name="Sex", choices=[(MALE, "M"), (FEMALE, "F")], max_length=10)
#     age = models.PositiveIntegerField(validators=[MinValueValidator(18), MaxValueValidator(50)], null=True)
    date_of_birth = models.DateField(null=True, validators=[validate_min_date_of_birth, validate_max_date_of_birth])
    level_of_education = models.CharField(max_length=100, null=True, choices=LEVEL_OF_EDUCATION,
                                          blank=False, default='Primary',
                                          verbose_name="Highest level of education completed")
    is_blocked = models.BooleanField(default=False)
    ea = models.ForeignKey('EnumerationArea', null=True, related_name="interviewers", verbose_name='Enumeration Area')
    language = models.CharField(max_length=100, null=True, choices=LANGUAGES,
                                blank=False, default='English', verbose_name="Preferred language of communication")
    weights = models.FloatField(default=0, blank=False)

    class Meta:
        app_label = 'survey'
        permissions = (
            ("can_view_interviewers", "Can view interviewers"),
        )

    def __unicode__(self):
        return self.name

    def total_households_completed(self, survey=None):
        try:
            if survey is None:
                survey = self.assignments.get(completed=False).survey
            return HouseSurveyCompletion.objects.filter(survey=survey, interviewer=self).distinct().count()
        except:
            return 0

    def total_households_batch_completed(self, batch):
        return HouseholdBatchCompletion.objects.filter(batch=batch, interviewer=self).distinct().count()


    def completed_batch_or_survey(self, survey, batch):
        if survey and not batch:
            return self.total_households_completed(survey) > 0
        return self.total_households_batch_completed(batch) > 0

    def locations_in_hierarchy(self):
        locs = self.ea.locations.all() #this should evaluate to country
        if locs:
            return locs[0].get_ancestors(include_self=True)
        else:
            Location.objects.none()

    @property
    def ussd_access(self):
        return USSDAccess.objects.filter(interviewer=self)

    @property
    def access_ids(self):
        accesses = self.intervieweraccess.all()
        ids = []
        if accesses.exists():
            ids = [acc.user_identifier for acc in accesses]
        return ids

    @property
    def odk_access(self):
        return ODKAccess.objects.filter(interviewer=self)
    
    def get_ussd_access(self, mobile_number):
        return USSDAccess.objects.get(interviewer=self, user_identifier=mobile_number)

    def get_odk_access(self, identifier):
        return ODKAccess.objects.get(interviewer=self, user_identifier=identifier)
    
    def present_households(self, survey=None):
        if survey is None:
            return Household.objects.filter(ea=self.ea)
        else:
            return Household.objects.filter(ea=self.ea, survey=survey)

    def may_commence(self, survey):
        total_registered = self.present_households(survey).count()
        registration_percent = total_registered * 100 / self.ea.total_households
        return registration_percent >= survey.min_percent_reg_houses
    
    def generate_survey_households(self, survey):
        survey_households = list(self.present_households(survey))
        if survey.has_sampling:
            #random select households as per sample size
            #first shuffle registered households and select up to sample number
            random.shuffle(survey_households)
            survey_households = survey_households[:survey.sample_size]
        return sorted(survey_households, key=lambda household: household.house_number)

    def has_survey(self):
        return self.assignments.filter(completed=True).count() > 0

class SurveyAllocation(BaseModel):
    interviewer = models.ForeignKey(Interviewer, related_name='assignments')
    survey = models.ForeignKey('Survey', related_name='work_allocation')
    completed = models.BooleanField(default=False)
    
    class Meta:
        app_label = 'survey'
    
    @classmethod
    def get_allocation(cls, interviewer):
        try:
            return cls.objects.get(interviewer=interviewer, completed=False).survey
        except cls.DoesNotExist:
            #allocate next unalocated survey
            open_surveys = interviewer.ea.open_surveys()
            allocations = cls.objects.filter(survey__pk__in=[survey.pk for survey in open_surveys], interviewer__ea=interviewer.ea).values_list('survey', flat=True)
            if allocations:
                available = [survey for survey in open_surveys if survey.pk not in allocations]
            else:
                available = open_surveys
            if available:
                survey = available[0]
                cls.objects.create(interviewer=interviewer, survey=survey)
                return survey
        return None