from datetime import date, datetime
from django.template.defaultfilters import slugify
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User, Group, Permission

from django.contrib.contenttypes.models import ContentType
from rapidsms.contrib.locations.models import Location, LocationType
from survey.models.locations import *
from survey.forms.filters import SurveyBatchFilterForm
from survey.models import GroupCondition, HouseholdMemberGroup, EnumerationArea, QuestionModule
from survey.models.batch import Batch
# from survey.models.batch_question_order import *
from survey.models.households import HouseholdHead, Household, HouseholdMember, HouseholdListing,SurveyHouseholdListing
from survey.models.backend import Backend
from survey.models.interviewer import Interviewer

from survey.models.questions import Question, QuestionOption
from survey.models.surveys import Survey
from survey.tests.base_test import BaseTest


class ExcelDownloadTest(BaseTest):

    def setUp(self):
        self.client = Client()
        HouseholdMemberGroup.objects.create(name="GENERAL", order=2)
        self.member_group = HouseholdMemberGroup.objects.create(name="Greater than 2 years", order=1)
        self.condition = GroupCondition.objects.create(attribute="AGE", value=2, condition="GREATER_THAN")
        self.condition.groups.add(self.member_group)

        self.survey = Survey.objects.create(name='survey name', description='survey descrpition',
                                            sample_size=10)
        self.batch = Batch.objects.create(order = 1, name="BATCH A", survey=self.survey)
        self.question_mod = QuestionModule.objects.create(name="Test question name",description="test desc")
        self.question_1 = Question.objects.create(identifier='123.1',text="This is a question123.1", answer_type='Numerical Answer',
                                           group=self.member_group,batch=self.batch,module=self.question_mod)
        self.question_2 = Question.objects.create(identifier='123.2',text="This is a question123.2", answer_type='Numerical Answer',
                                           group=self.member_group,batch=self.batch,module=self.question_mod)
        self.option_1_1 = QuestionOption.objects.create(question=self.question_2, text="OPTION 1", order=1)
        self.option_1_2 = QuestionOption.objects.create(question=self.question_2, text="OPTION 2", order=2)
        self.option_1_3 = QuestionOption.objects.create(question=self.question_2, text="Others", order=3)
        sub_question_1 = Question.objects.create(identifier='123.3',text="This is a question123.3", answer_type='Numerical Answer',
                                           group=self.member_group,batch=self.batch,module=self.question_mod)

        self.question_3 = Question.objects.create(identifier='123.4',text="This is a question123.4", answer_type='Numerical Answer',
                                           group=self.member_group,batch=self.batch,module=self.question_mod)

        country = LocationType.objects.create(name="Country", slug="country")
        uganda = Location.objects.create(name="Uganda", type=country,code="1")
        district = LocationType.objects.create(name='District', parent=country,slug='district')
        kampala = Location.objects.create(name="Kampala", type=district,parent=uganda,code="2")
        ea = EnumerationArea.objects.create(name="Kampala EA")
        ea.locations.add(kampala)

        backend = Backend.objects.create(name='something')
        self.investigator = Interviewer.objects.create(name="Investigator",
                                                   ea=ea,
                                                   gender='1',level_of_education='Primary',
                                                   language='Eglish',weights=0)
        household_listing = HouseholdListing.objects.create(ea=ea,list_registrar=self.investigator,initial_survey=self.survey)
        self.household = Household.objects.create(house_number=123456,listing=household_listing,physical_address='Test address',
                                             last_registrar=self.investigator,registration_channel="ODK Access",head_desc="Head",
                                             head_sex='MALE')
        survey_householdlisting = SurveyHouseholdListing.objects.create(listing=household_listing,survey=self.survey)
        self.household_head = HouseholdHead.objects.create(surname="sur", first_name='fir', gender='MALE', date_of_birth="1988-01-01",
                                                          household=self.household,survey_listing=survey_householdlisting,
                                                          registrar=self.investigator,registration_channel="ODK Access",
                                                      occupation="Agricultural labor",level_of_education="Primary",
                                                      resident_since='1989-02-02')

        raj = self.assign_permission_to(User.objects.create_user('Rajni', 'rajni@kant.com', 'I_Rock'), 'can_view_aggregates')
        user_without_permission = User.objects.create_user(username='useless', email='rajni@kant.com', password='I_Suck')
        self.client.login(username='Rajni', password='I_Rock')

    def test_downloaded_excel_file(self):
        file_name = "%s.csv" % self.batch.name
        data = {'batch': self.batch.pk, 'survey': self.batch.survey.pk}
        response = self.client.get('/aggregates/spreadsheet_report', data=data)
        self.assertEquals(200, response.status_code)
        self.assertEquals(response.get('Content-Type'), "text/html; charset=utf-8")

    def test_downloaded_excel_when_only_survey_supplied(self):
        batchB = Batch.objects.create(order=2, name="different batch", survey=self.survey)
        question_1B = Question.objects.create(identifier='123.7',text="This is a question123.7", answer_type='Numerical Answer',
                                           group=self.member_group,batch=self.batch,module=self.question_mod)
        question_2B = Question.objects.create(identifier='123.5',text="This is a question123.5", answer_type='Numerical Answer',
                                           group=self.member_group,batch=self.batch,module=self.question_mod)
        question_3B = Question.objects.create(identifier='123.6',text="This is a question123.6", answer_type='Numerical Answer',
                                           group=self.member_group,batch=self.batch,module=self.question_mod)

        yes_option = QuestionOption.objects.create(question=question_1B, text="OPTION 1", order=1)
        no_option = QuestionOption.objects.create(question=question_1B, text="OPTION 2", order=2)

        header_structure = ['Location', 'Household ID', 'Name', 'Age', 'Month of Birth', 'Year of Birth', 'Gender',
                            self.question_1.identifier, self.question_2.identifier, '', self.question_3.identifier,
                            question_1B.identifier, question_2B.identifier, '', question_3B.identifier]

        expected_csv_data = ['Kampala', self.household.physical_address, 'Surname', '14', '9',  '2000',   'Male',
                             '1',       '1', 'OPTION 1',  'ANSWER', str(1), str(no_option.order), no_option.text, '1']

        contents = "%s\r\n%s\r\n" % (",".join(header_structure), ",".join(expected_csv_data))

        file_name = "%s.csv" % self.survey.name
        response = self.client.get('/aggregates/spreadsheet_report', data={'survey': self.survey.pk, 'batch':''})
        self.assertEquals(200, response.status_code)
        self.assertEquals(response.get('Content-Type'), "text/html; charset=utf-8")

    def test_restricted_permssion(self):
        self.assert_restricted_permission_for('/aggregates/spreadsheet_report')


class ExcelDownloadViewTest(BaseTest):

    def test_get(self):
        client = Client()
        raj = User.objects.create_user('Rajni', 'rajni@kant.com', 'I_Rock')
        user_without_permission = User.objects.create_user(username='useless', email='rajni@kant.com', password='I_Suck')

        some_group = Group.objects.create(name='some group')
        auth_content = ContentType.objects.get_for_model(Permission)
        permission, out = Permission.objects.get_or_create(codename='can_view_aggregates', content_type=auth_content)
        some_group.permissions.add(permission)
        some_group.user_set.add(raj)

        self.client.login(username='Rajni', password='I_Rock')
        Survey.objects.create(name="survey")

        response = self.client.get('/aggregates/download_spreadsheet')
        self.failUnlessEqual(response.status_code, 200)
        templates = [template.name for template in response.templates]
        self.assertIn('aggregates/download_excel.html', templates)
        self.assertIsInstance(response.context['survey_batch_filter_form'], SurveyBatchFilterForm)

    def test_restricted_permssion(self):
        self.assert_restricted_permission_for('/aggregates/download_spreadsheet')


class ReportForCompletedInvestigatorTest(BaseTest):
    def setUp(self):
        self.client = Client()
        raj = User.objects.create_user('Rajni', 'rajni@kant.com', 'I_Rock')
        User.objects.create_user(username='useless', email='rajni@kant.com', password='I_Suck')
        self.question_mod = QuestionModule.objects.create(name="Test question name",description="test desc")
        self.survey = Survey.objects.create(name='some group')
        self.batch = Batch.objects.create(name='BatchA', survey=self.survey)
        some_group = Group.objects.create(name='some group')
        auth_content = ContentType.objects.get_for_model(Permission)
        permission, out = Permission.objects.get_or_create(codename='can_view_aggregates', content_type=auth_content)
        some_group.permissions.add(permission)
        some_group.user_set.add(raj)

        self.client.login(username='Rajni', password='I_Rock')

    def test_should_have_header_fields_in_download_report(self):
        survey = Survey.objects.create(name='some survey')
        file_name = "interviewer.csv"
        response = self.client.post('/interviewers/completed/download/', {'survey': survey.id})
        self.assertEquals(200, response.status_code)
        self.assertEquals(response.get('Content-Type'), "text/csv")
        self.assertEquals(response.get('Content-Disposition'), 'attachment; filename="%s"' % file_name)
        row1 = ['Interviewer', 'Access Channels']
        row1.extend(list(LocationType.objects.all().values_list('name', flat=True)))
        contents = "%s\r\n" % (",".join(row1))
        self.assertEquals(contents, response.content)

    def test_should_have_investigators_who_completed_a_selected_batch(self):
        country = LocationType.objects.create(name="Country", slug="country")
        district = LocationType.objects.create(name="District", parent=country, slug="district")
        city = LocationType.objects.create(name="City", parent=district, slug="city")
        uganda = Location.objects.create(name="Uganda", type=country)
        abim = Location.objects.create(name="Abim", type=district, parent=uganda)
        kampala = Location.objects.create(name="Kampala", type=city, parent=abim)
        ea = EnumerationArea.objects.create(name="EA2")
        ea.locations.add(kampala)


        backend = Backend.objects.create(name='something')
        survey = Survey.objects.create(name='SurveyA')
        batch = Batch.objects.create(name='Batch A')

        investigator_1 = Interviewer.objects.create(name="Investigator_1",
                                                   ea=ea,
                                                   gender='1',level_of_education='Primary',
                                                   language='Eglish',weights=0)
        investigator_2 = Interviewer.objects.create(name="Investigator_2",
                                                   ea=ea,
                                                   gender='1',level_of_education='Primary',
                                                   language='Eglish',weights=0)
        household_listing_1 = HouseholdListing.objects.create(ea=ea,list_registrar=investigator_1,initial_survey=survey)
        household_1 = Household.objects.create(house_number=223456,listing=household_listing_1,physical_address='Test address',
                                             last_registrar=investigator_1,registration_channel="ODK Access",head_desc="Head",
                                             head_sex='MALE')
        # household_listing_2 = HouseholdListing.objects.create(ea=ea,list_registrar=investigator_2,initial_survey=survey)
        household_2 = Household.objects.create(house_number=223457,listing=household_listing_1,physical_address='Test address',
                                             last_registrar=investigator_2,registration_channel="ODK Access",head_desc="Head",
                                             head_sex='MALE')

        member_group = HouseholdMemberGroup.objects.create(name='group1', order=1)
        question_1 = Question.objects.create(identifier='123.10',text="This is a question123.10", answer_type='Numerical Answer',
                                           group=member_group,batch=batch,module=self.question_mod)
        survey_householdlisting = SurveyHouseholdListing.objects.create(listing=household_listing_1,survey=survey)
        member_1 = HouseholdMember.objects.create(surname="sur", first_name='fir', gender='MALE', date_of_birth="1988-01-01",
                                                          household=household_1,survey_listing=survey_householdlisting,
                                                          registrar=investigator_1,registration_channel="ODK Access")
        member_2 = HouseholdMember.objects.create(surname="sur123", first_name='fir123', gender='MALE', date_of_birth="1988-01-01",
                                                          household=household_1,survey_listing=survey_householdlisting,
                                                          registrar=investigator_1,registration_channel="ODK Access")
        HouseholdMember.objects.create(surname="su234r", first_name='fir234', gender='MALE', date_of_birth="1988-01-01",
                                                          household=household_2,survey_listing=survey_householdlisting,
                                                          registrar=investigator_2,registration_channel="ODK Access")
        expected_data = [investigator_1.name]
        unexpected_data = [investigator_2.name]

        post_data = {'survey': survey.id, 'batch': batch.id}
        response = self.client.post('/investigators/completed/download/', post_data)
        row1 = ['Investigator', 'Phone Number']
        row1.extend(list(LocationType.objects.all().values_list('name', flat=True)))
        contents = "%s\r\n" % (",".join(row1))
        # self.assertIn(contents, response.content)
        # [self.assertIn(investigator_details, response.content) for investigator_details in expected_data]
        [self.assertNotIn(investigator_details, response.content) for investigator_details in unexpected_data]
#
    def test_restricted_permission(self):
        self.assert_login_required('/interviewers/completed/download/')
        self.assert_restricted_permission_for('/interviewers/completed/download/')
        self.assert_restricted_permission_for('/interviewer_report/')

    def test_should_get_view_for_download(self):
        response = self.client.get('/interviewer_report/')
        self.assertEqual(200, response.status_code)
        templates = [template.name for template in response.templates]
        self.assertIn('aggregates/download_interviewer.html', templates)