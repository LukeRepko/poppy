# Copyright (c) 2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import uuid

import ddt
import mock
from mock import ANY
from nose.tools import raises
from oslo_config import cfg

from poppy.model import ssl_certificate
from poppy.storage.cassandra import certificates
from poppy.storage.cassandra import driver
from tests.unit import base


@ddt.ddt
class CassandraStorageCertificateTests(base.TestCase):

    def setUp(self):
        super(CassandraStorageCertificateTests, self).setUp()

        # mock arguments to use
        self.project_id = '123456'
        self.service_id = uuid.uuid4()
        self.service_name = 'mocksite'

        # create mocked config and driver
        conf = cfg.ConfigOpts()
        conf.register_opt(
            cfg.StrOpt(
                'datacenter',
                default='',
                help='datacenter where the C* cluster hosted'))
        conf.register_opts(driver.CASSANDRA_OPTIONS,
                           group=driver.CASSANDRA_GROUP)
        cassandra_driver = driver.CassandraStorageDriver(conf)

        migrations_patcher = mock.patch(
            'cdeploy.migrator.Migrator'
        )
        migrations_patcher.start()
        self.addCleanup(migrations_patcher.stop)

        cluster_patcher = mock.patch('cassandra.cluster.Cluster')
        self.mock_cluster = cluster_patcher.start()
        self.mock_session = self.mock_cluster().connect()
        self.addCleanup(cluster_patcher.stop)

        # stubbed cassandra driver
        self.cc = certificates.CertificatesController(cassandra_driver)

    @ddt.file_data('data_get_certs_by_domain.json')
    def test_get_certs_by_domain(self, cert_details_json):
        """Test for getting certificate by given domain name.

        Mock the cassandra response to have below values:
            - flavor_id as 'flavor1'
            - cert_type as 'san'
            - valid 'cert_details' details

        Call the ``get_certs_by_domain`` with the correct values.
        Expect that the method constructs and returns a correct
        ``SSLCertificate`` object.

        :param list cert_details_json: List of dicts that holds values
            to mock the cassandra response
        """
        self.mock_session.execute.return_value = cert_details_json[0]
        args = {
            'domain_name': 'www.mydomain.com',
        }
        ssl_cert = self.cc.get_certs_by_domain('www.mydomain.com',
                                               flavor_id='flavor1',
                                               cert_type='san')
        self.assertTrue(isinstance(ssl_cert, ssl_certificate.SSLCertificate))
        self.assertEqual(ssl_cert.flavor_id, 'flavor1')
        self.assertEqual(ssl_cert.project_id, '12345')
        self.assertEqual(ssl_cert.cert_type, 'san')
        self.mock_session.execute.assert_called_with(ANY, args)

    @raises(ValueError)
    @ddt.file_data('data_get_certs_by_domain.json')
    def test_get_certs_by_domain_non_none(self, cert_details_json):
        """Test for verifying the input parameters.

        Mock the cassandra response to have the below values
            - flavor_id as 'flavor1'
            - cert_type as 'san'

        But call the ``get_certs_by_domain`` with different values for
        flavor_id and cert_type.

        Expect that the returned values from cassandra not matching
        with the passed parameters; eventually raising an ValueError.

        :param list cert_details_json: List of dicts that holds values
            to mock the cassandra response
        """
        self.mock_session.execute.return_value = cert_details_json[0]
        self.cc.get_certs_by_domain(
            domain_name="www.mydomain.com",
            flavor_id='flavor2',
            cert_type='sni'
        )

    @raises(ValueError)
    def test_get_certs_by_domain_not_exists(self):
        """Test for a domain that does not have certificate.

        Call the ``get_certs_by_domain()``
        with a random domain name for which there is no
        certificate created yet.

        Should receive an Exception.
        """
        self.cc.get_certs_by_domain(
                             domain_name="www.randomdomain.com")

    def test_get_certs_by_status(self):
        # mock the response from cassandra
        self.mock_session.execute.return_value = \
            [{"domain_name": "www.example.com"}]
        actual_response = self.cc.get_certs_by_status(
            status="deployed")
        self.assertEqual(actual_response,
                         [{"domain_name": "www.example.com"}])

        self.mock_session.execute.return_value = \
            [{"domain_name": "www.example1.com"}]
        actual_response = self.cc.get_certs_by_status(
            status="failed")
        self.assertEqual(actual_response,
                         [{"domain_name": "www.example1.com"}])

    @ddt.file_data('data_get_certs_by_domain.json')
    def test_create_cert_already_exists(self, cert_details_json):
        # mock the response from cassandra
        self.mock_session.execute.return_value = cert_details_json[0]

        ssl_cert_obj = ssl_certificate.SSLCertificate(
            'flavor1',
            'www.mydomain.com',
            'san'
        )
        self.assertRaises(
            ValueError,
            self.cc.create_certificate, '12345', ssl_cert_obj
        )

    @ddt.file_data('data_get_certs_by_domain.json')
    def test_delete_cert(self, cert_details_json):
        # mock the response from cassandra
        self.mock_session.execute.return_value = cert_details_json[0]

        try:
            self.cc.delete_certificate('12345', 'www.mydomain.com', 'san')
        except Exception as e:
            self.fail(e)

    def test_create_certificate_with_cert_status_in_details(self):
        ssl_cert_obj = ssl_certificate.SSLCertificate(
            'flavor1',
            'www.mydomain.com',
            'san',
            project_id='12345',
            cert_details={
                "provider": "{\"cert_domain\": \"abc\", \"extra_info\": "
                            "{ \"status\": \"deployed\", \"san_cert\": \""
                            "awesome_san\", \"action\": \"Ready\"}}"
            }
        )

        try:
            self.cc.create_certificate('12345', ssl_cert_obj)
        except Exception as e:
            self.fail(e)

    def test_update_certificate_with_cert_status_in_details(self):
        ssl_cert_obj = ssl_certificate.SSLCertificate(
            'flavor1',
            'www.mydomain.com',
            'san',
            project_id='12345',
            cert_details={
                "provider": "{\"cert_domain\": \"abc\", \"extra_info\": "
                            "{ \"status\": \"deployed\", \"san_cert\": \""
                            "awesome_san\", \"action\": \"Ready\"}}"
            }
        )

        try:
            self.cc.update_certificate(
                'www.mydomain.com', 'san', 'flavor1',
                ssl_cert_obj.cert_details
            )
        except Exception as e:
            self.fail(e)
