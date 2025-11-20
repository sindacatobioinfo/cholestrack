# users/test_rbac.py
"""
Automated tests for Role-Based Access Control (RBAC) implementation.

Tests verify that:
1. UserRole permission methods work correctly
2. Role decorators properly restrict view access
3. Different user roles have appropriate permissions
4. Unauthorized access is properly denied
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from users.models import UserRole, EmailVerification
from samples.models import Patient
from files.models import AnalysisFileLocation


class UserRolePermissionMethodsTest(TestCase):
    """
    Test the permission methods defined in the UserRole model.
    """

    def setUp(self):
        """Create test users with different roles."""
        # Admin user
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            is_active=True
        )
        EmailVerification.objects.create(
            user=self.admin_user,
            verification_token='admin_token',
            email_confirmed=True
        )
        self.admin_role = UserRole.objects.create(
            user=self.admin_user,
            role='ADMIN',
            confirmed_by_admin=True
        )

        # Data Manager user
        self.data_manager_user = User.objects.create_user(
            username='data_manager_test',
            email='datamanager@test.com',
            password='testpass123',
            is_active=True
        )
        EmailVerification.objects.create(
            user=self.data_manager_user,
            verification_token='dm_token',
            email_confirmed=True
        )
        self.data_manager_role = UserRole.objects.create(
            user=self.data_manager_user,
            role='DATA_MANAGER',
            confirmed_by_admin=True
        )

        # Researcher user
        self.researcher_user = User.objects.create_user(
            username='researcher_test',
            email='researcher@test.com',
            password='testpass123',
            is_active=True
        )
        EmailVerification.objects.create(
            user=self.researcher_user,
            verification_token='researcher_token',
            email_confirmed=True
        )
        self.researcher_role = UserRole.objects.create(
            user=self.researcher_user,
            role='RESEARCHER',
            confirmed_by_admin=True
        )

        # Clinician user
        self.clinician_user = User.objects.create_user(
            username='clinician_test',
            email='clinician@test.com',
            password='testpass123',
            is_active=True
        )
        EmailVerification.objects.create(
            user=self.clinician_user,
            verification_token='clinician_token',
            email_confirmed=True
        )
        self.clinician_role = UserRole.objects.create(
            user=self.clinician_user,
            role='CLINICIAN',
            confirmed_by_admin=True
        )

        # Unconfirmed user
        self.unconfirmed_user = User.objects.create_user(
            username='unconfirmed_test',
            email='unconfirmed@test.com',
            password='testpass123',
            is_active=True
        )
        EmailVerification.objects.create(
            user=self.unconfirmed_user,
            verification_token='unconfirmed_token',
            email_confirmed=True
        )
        self.unconfirmed_role = UserRole.objects.create(
            user=self.unconfirmed_user,
            role='CLINICIAN',
            confirmed_by_admin=False  # Not confirmed by admin
        )

    def test_admin_has_all_permissions(self):
        """Admin should have all permissions."""
        self.assertTrue(self.admin_role.can_create_patient())
        self.assertTrue(self.admin_role.can_edit_patient())
        self.assertTrue(self.admin_role.can_delete_patient())
        self.assertTrue(self.admin_role.can_create_file())
        self.assertTrue(self.admin_role.can_edit_file())
        self.assertTrue(self.admin_role.can_delete_file())
        self.assertTrue(self.admin_role.can_download_files())
        self.assertTrue(self.admin_role.can_view_samples())

    def test_data_manager_permissions(self):
        """Data Manager should have create/edit/view/delete permissions."""
        self.assertTrue(self.data_manager_role.can_create_patient())
        self.assertTrue(self.data_manager_role.can_edit_patient())
        self.assertTrue(self.data_manager_role.can_delete_patient())
        self.assertTrue(self.data_manager_role.can_create_file())
        self.assertTrue(self.data_manager_role.can_edit_file())
        self.assertTrue(self.data_manager_role.can_delete_file())
        self.assertTrue(self.data_manager_role.can_download_files())
        self.assertTrue(self.data_manager_role.can_view_samples())

    def test_researcher_permissions(self):
        """Researcher should have create/edit/view but NOT delete permissions."""
        self.assertTrue(self.researcher_role.can_create_patient())
        self.assertTrue(self.researcher_role.can_edit_patient())
        self.assertFalse(self.researcher_role.can_delete_patient())  # Cannot delete
        self.assertTrue(self.researcher_role.can_create_file())
        self.assertTrue(self.researcher_role.can_edit_file())
        self.assertFalse(self.researcher_role.can_delete_file())  # Cannot delete
        self.assertTrue(self.researcher_role.can_download_files())
        self.assertTrue(self.researcher_role.can_view_samples())

    def test_clinician_permissions(self):
        """Clinician should only have view/download permissions."""
        self.assertFalse(self.clinician_role.can_create_patient())
        self.assertFalse(self.clinician_role.can_edit_patient())
        self.assertFalse(self.clinician_role.can_delete_patient())
        self.assertFalse(self.clinician_role.can_create_file())
        self.assertFalse(self.clinician_role.can_edit_file())
        self.assertFalse(self.clinician_role.can_delete_file())
        self.assertTrue(self.clinician_role.can_download_files())
        self.assertTrue(self.clinician_role.can_view_samples())

    def test_unconfirmed_user_has_no_permissions(self):
        """Unconfirmed user should have no permissions."""
        self.assertFalse(self.unconfirmed_role.can_create_patient())
        self.assertFalse(self.unconfirmed_role.can_edit_patient())
        self.assertFalse(self.unconfirmed_role.can_delete_patient())
        self.assertFalse(self.unconfirmed_role.can_create_file())
        self.assertFalse(self.unconfirmed_role.can_edit_file())
        self.assertFalse(self.unconfirmed_role.can_delete_file())
        self.assertFalse(self.unconfirmed_role.can_download_files())
        self.assertFalse(self.unconfirmed_role.can_view_samples())


class SampleViewsRBACTest(TestCase):
    """
    Test RBAC enforcement in samples app views.
    """

    def setUp(self):
        """Create test users and sample data."""
        # Create users with different roles (similar to above)
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            is_active=True
        )
        EmailVerification.objects.create(
            user=self.admin_user,
            verification_token='admin_token',
            email_confirmed=True
        )
        UserRole.objects.create(
            user=self.admin_user,
            role='ADMIN',
            confirmed_by_admin=True
        )

        self.researcher_user = User.objects.create_user(
            username='researcher_test',
            email='researcher@test.com',
            password='testpass123',
            is_active=True
        )
        EmailVerification.objects.create(
            user=self.researcher_user,
            verification_token='researcher_token',
            email_confirmed=True
        )
        UserRole.objects.create(
            user=self.researcher_user,
            role='RESEARCHER',
            confirmed_by_admin=True
        )

        self.clinician_user = User.objects.create_user(
            username='clinician_test',
            email='clinician@test.com',
            password='testpass123',
            is_active=True
        )
        EmailVerification.objects.create(
            user=self.clinician_user,
            verification_token='clinician_token',
            email_confirmed=True
        )
        UserRole.objects.create(
            user=self.clinician_user,
            role='CLINICIAN',
            confirmed_by_admin=True
        )

        # Create test patient
        self.patient = Patient.objects.create(
            patient_id='TEST_001',
            name='Test Patient',
            main_exome_result='Negative',
            responsible_user=self.admin_user
        )

        self.client = Client()

    def test_sample_list_accessible_to_all_confirmed_users(self):
        """All confirmed users should be able to view sample list."""
        # Test as admin
        self.client.login(username='admin_test', password='testpass123')
        response = self.client.get(reverse('samples:sample_list'))
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # Test as researcher
        self.client.login(username='researcher_test', password='testpass123')
        response = self.client.get(reverse('samples:sample_list'))
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # Test as clinician
        self.client.login(username='clinician_test', password='testpass123')
        response = self.client.get(reverse('samples:sample_list'))
        self.assertEqual(response.status_code, 200)
        self.client.logout()

    def test_patient_create_denied_for_clinician(self):
        """Clinician should NOT be able to create patients."""
        self.client.login(username='clinician_test', password='testpass123')
        response = self.client.get(reverse('samples:patient_create'))
        # Should redirect or show error, not 200
        self.assertNotEqual(response.status_code, 200)
        self.client.logout()

    def test_patient_create_allowed_for_researcher(self):
        """Researcher should be able to create patients."""
        self.client.login(username='researcher_test', password='testpass123')
        response = self.client.get(reverse('samples:patient_create'))
        self.assertEqual(response.status_code, 200)
        self.client.logout()

    def test_patient_create_allowed_for_admin(self):
        """Admin should be able to create patients."""
        self.client.login(username='admin_test', password='testpass123')
        response = self.client.get(reverse('samples:patient_create'))
        self.assertEqual(response.status_code, 200)
        self.client.logout()

    def test_patient_edit_denied_for_clinician(self):
        """Clinician should NOT be able to edit patients."""
        self.client.login(username='clinician_test', password='testpass123')
        response = self.client.get(
            reverse('samples:patient_edit', kwargs={'patient_id': self.patient.patient_id})
        )
        self.assertNotEqual(response.status_code, 200)
        self.client.logout()

    def test_patient_edit_allowed_for_researcher(self):
        """Researcher should be able to edit patients."""
        self.client.login(username='researcher_test', password='testpass123')
        response = self.client.get(
            reverse('samples:patient_edit', kwargs={'patient_id': self.patient.patient_id})
        )
        self.assertEqual(response.status_code, 200)
        self.client.logout()

    def test_patient_delete_denied_for_researcher(self):
        """Researcher should NOT be able to delete patients."""
        self.client.login(username='researcher_test', password='testpass123')
        response = self.client.get(
            reverse('samples:patient_delete', kwargs={'patient_id': self.patient.patient_id})
        )
        self.assertNotEqual(response.status_code, 200)
        self.client.logout()

    def test_patient_delete_denied_for_clinician(self):
        """Clinician should NOT be able to delete patients."""
        self.client.login(username='clinician_test', password='testpass123')
        response = self.client.get(
            reverse('samples:patient_delete', kwargs={'patient_id': self.patient.patient_id})
        )
        self.assertNotEqual(response.status_code, 200)
        self.client.logout()

    def test_patient_delete_allowed_for_admin(self):
        """Admin should be able to delete patients."""
        self.client.login(username='admin_test', password='testpass123')
        response = self.client.get(
            reverse('samples:patient_delete', kwargs={'patient_id': self.patient.patient_id})
        )
        self.assertEqual(response.status_code, 200)
        self.client.logout()


class FileViewsRBACTest(TestCase):
    """
    Test RBAC enforcement in files app views.
    """

    def setUp(self):
        """Create test users and file data."""
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            is_active=True
        )
        EmailVerification.objects.create(
            user=self.admin_user,
            verification_token='admin_token',
            email_confirmed=True
        )
        UserRole.objects.create(
            user=self.admin_user,
            role='ADMIN',
            confirmed_by_admin=True
        )

        # Create researcher user
        self.researcher_user = User.objects.create_user(
            username='researcher_test',
            email='researcher@test.com',
            password='testpass123',
            is_active=True
        )
        EmailVerification.objects.create(
            user=self.researcher_user,
            verification_token='researcher_token',
            email_confirmed=True
        )
        UserRole.objects.create(
            user=self.researcher_user,
            role='RESEARCHER',
            confirmed_by_admin=True
        )

        # Create clinician user
        self.clinician_user = User.objects.create_user(
            username='clinician_test',
            email='clinician@test.com',
            password='testpass123',
            is_active=True
        )
        EmailVerification.objects.create(
            user=self.clinician_user,
            verification_token='clinician_token',
            email_confirmed=True
        )
        UserRole.objects.create(
            user=self.clinician_user,
            role='CLINICIAN',
            confirmed_by_admin=True
        )

        # Create test patient and file
        self.patient = Patient.objects.create(
            patient_id='TEST_001',
            name='Test Patient',
            main_exome_result='Negative',
            responsible_user=self.admin_user
        )

        self.file_location = AnalysisFileLocation.objects.create(
            patient=self.patient,
            file_type='VCF',
            file_path='test/path/file.vcf',
            sample_id='SAMPLE_001',
            project_name='Test Project',
            batch_id='BATCH_001',
            data_type='WES',
            server_name='SERVER_1',
            uploaded_by=self.admin_user,
            is_active=True
        )

        self.client = Client()

    def test_file_upload_denied_for_clinician(self):
        """Clinician should NOT be able to register files."""
        self.client.login(username='clinician_test', password='testpass123')
        response = self.client.get(reverse('files:file_upload'))
        self.assertNotEqual(response.status_code, 200)
        self.client.logout()

    def test_file_upload_allowed_for_researcher(self):
        """Researcher should be able to register files."""
        self.client.login(username='researcher_test', password='testpass123')
        response = self.client.get(reverse('files:file_upload'))
        self.assertEqual(response.status_code, 200)
        self.client.logout()

    def test_file_upload_allowed_for_admin(self):
        """Admin should be able to register files."""
        self.client.login(username='admin_test', password='testpass123')
        response = self.client.get(reverse('files:file_upload'))
        self.assertEqual(response.status_code, 200)
        self.client.logout()

    def test_file_edit_denied_for_clinician(self):
        """Clinician should NOT be able to edit file metadata."""
        self.client.login(username='clinician_test', password='testpass123')
        response = self.client.get(
            reverse('files:file_edit', kwargs={'file_location_id': self.file_location.id})
        )
        self.assertNotEqual(response.status_code, 200)
        self.client.logout()

    def test_file_edit_allowed_for_researcher(self):
        """Researcher should be able to edit file metadata."""
        self.client.login(username='researcher_test', password='testpass123')
        response = self.client.get(
            reverse('files:file_edit', kwargs={'file_location_id': self.file_location.id})
        )
        self.assertEqual(response.status_code, 200)
        self.client.logout()

    def test_file_delete_denied_for_researcher(self):
        """Researcher should NOT be able to delete files."""
        self.client.login(username='researcher_test', password='testpass123')
        response = self.client.get(
            reverse('files:file_delete', kwargs={'file_location_id': self.file_location.id})
        )
        self.assertNotEqual(response.status_code, 200)
        self.client.logout()

    def test_file_delete_denied_for_clinician(self):
        """Clinician should NOT be able to delete files."""
        self.client.login(username='clinician_test', password='testpass123')
        response = self.client.get(
            reverse('files:file_delete', kwargs={'file_location_id': self.file_location.id})
        )
        self.assertNotEqual(response.status_code, 200)
        self.client.logout()

    def test_file_delete_allowed_for_admin(self):
        """Admin should be able to delete files."""
        self.client.login(username='admin_test', password='testpass123')
        response = self.client.get(
            reverse('files:file_delete', kwargs={'file_location_id': self.file_location.id})
        )
        self.assertEqual(response.status_code, 200)
        self.client.logout()


class RoleDecoratorTest(TestCase):
    """
    Test the @role_required decorator functionality.
    """

    def setUp(self):
        """Create test users."""
        # User without email verification
        self.unverified_user = User.objects.create_user(
            username='unverified_test',
            email='unverified@test.com',
            password='testpass123',
            is_active=True
        )
        EmailVerification.objects.create(
            user=self.unverified_user,
            verification_token='unverified_token',
            email_confirmed=False  # Not verified
        )

        # User without role
        self.no_role_user = User.objects.create_user(
            username='norole_test',
            email='norole@test.com',
            password='testpass123',
            is_active=True
        )
        EmailVerification.objects.create(
            user=self.no_role_user,
            verification_token='norole_token',
            email_confirmed=True
        )
        # No UserRole created for this user

        # User with unconfirmed role
        self.unconfirmed_user = User.objects.create_user(
            username='unconfirmed_test',
            email='unconfirmed@test.com',
            password='testpass123',
            is_active=True
        )
        EmailVerification.objects.create(
            user=self.unconfirmed_user,
            verification_token='unconfirmed_token',
            email_confirmed=True
        )
        UserRole.objects.create(
            user=self.unconfirmed_user,
            role='CLINICIAN',
            confirmed_by_admin=False  # Not confirmed
        )

        self.client = Client()

    def test_unverified_email_denied_access(self):
        """User without email verification should be denied access."""
        self.client.login(username='unverified_test', password='testpass123')
        response = self.client.get(reverse('samples:patient_create'))
        # Should redirect, not 200
        self.assertNotEqual(response.status_code, 200)
        self.client.logout()

    def test_no_role_denied_access(self):
        """User without role should be denied access."""
        self.client.login(username='norole_test', password='testpass123')
        response = self.client.get(reverse('samples:patient_create'))
        # Should redirect, not 200
        self.assertNotEqual(response.status_code, 200)
        self.client.logout()

    def test_unconfirmed_role_denied_access(self):
        """User with unconfirmed role should be denied access."""
        self.client.login(username='unconfirmed_test', password='testpass123')
        response = self.client.get(reverse('samples:patient_create'))
        # Should redirect, not 200
        self.assertNotEqual(response.status_code, 200)
        self.client.logout()
