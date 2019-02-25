import mock
from ..helpers import BaseApplicationTest
from dmutils.forms import FakeCsrf
from dmutils.email import EmailError
from dmapiclient import HTTPError
from io import BytesIO
import json


def get_application(id):
    return {'application': {
        'id': 1,
        'status': 'saved',
        'data': {'a': 'b'},
        'created_at': '2016-11-14 01:22:01.14119',
        'email': 'applicant@email.com',
        'representative': 'Ms Authorised Rep',
        'name': 'My Amazing Company'
    }}


def get_unauthorised_application(id):
    return {'application': {
        'id': 1,
        'status': 'saved',
        'data': {'a': 'b'},
        'created_at': '2016-11-14 01:22:01.14119',
        'email': 'test@email.com',
        'representative': 'Ms Authorised Rep',
        'name': 'My Amazing Company'
    }}


def get_submitted_application(id):
    return {'application': {
        'id': 1,
        'status': 'submitted',
        'data': {'a': 'b'},
        'created_at': '2016-11-14 01:22:01.14119',
    }}


def get_another_application(id):
    return {'application': {
        'id': 2,
        'status': 'saved',
        'data': {'a': 'b'},
        'created_at': '2016-11-14 01:22:01.14119',
    }}


class TestDocuments(BaseApplicationTest):

    def setup(self):
        super(TestDocuments, self).setup()

    @mock.patch("app.main.views.signup.data_api_client")
    @mock.patch('app.main.views.signup.s3_download_file')
    def test_document_download(self, download_file, data_api_client):
        output = BytesIO()
        output.write('test file contents')
        download_file.return_value = output.getvalue()

        with self.app.test_client():
            self.login_as_applicant()
            data_api_client.get_application.side_effect = get_application
            res = self.client.get(self.expand_path('/application/1/documents/test.pdf'))

            assert res.status_code == 200
            assert res.mimetype == 'application/pdf'
            assert res.data == 'test file contents'
            download_file.assert_called_once_with('test.pdf', 'applications/1')

    @mock.patch("app.main.views.signup.data_api_client")
    @mock.patch('app.main.views.signup.s3_upload_file_from_request')
    def test_document_upload(self, upload_file, data_api_client):
        upload_file.return_value = 'test.pdf'

        with self.app.test_request_context():
            self.login_as_applicant()
            data_api_client.get_application.side_effect = get_application
            res = self.client.post(
                self.expand_path('/application/1/documents/test'),
                data={'csrf_token': FakeCsrf.valid_token}
            )

            assert res.status_code == 200
            assert res.data == 'test.pdf'
            upload_file.assert_called_once_with(mock.ANY, 'test', 'applications/1')
