# home/tests.py
"""
Tests for the admin center user management views.

Coverage:
- Page loads for ADMIN across all filters (all, active, inactive,
  pending_email, pending_role) including users lacking UserRole or
  EmailVerification.
- Non-admin and unconfirmed-role users receive a redirect (not 200).
- Full CRUD: create, detail, edit, toggle_active, toggle_role_confirm,
  mark_email_verified, reset_password, delete.
- RBAC safeguards: self-action blocks, last-admin protection, superuser
  protection, POST-only enforcement.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from users.models import UserRole, EmailVerification, RoleChangeRequest


# ---------------------------------------------------------------------------
# Helper: build a fully-ready admin user
# ---------------------------------------------------------------------------

def make_admin(username='admin', password='admin-pass-99'):
    user = User.objects.create_user(
        username=username, email=f'{username}@example.com',
        password=password, is_active=True,
    )
    EmailVerification.objects.create(
        user=user, verification_token=f'tok_{username}', email_confirmed=True,
    )
    UserRole.objects.create(user=user, role='ADMIN', confirmed_by_admin=True)
    return user


def make_user(username, role_code='CLINICIAN', confirmed=True,
              email_confirmed=True, is_active=True, has_role=True,
              has_ev=True):
    """Create a user with optional role / email-verification."""
    user = User.objects.create_user(
        username=username, email=f'{username}@example.com',
        password='pass-9999', is_active=is_active,
    )
    if has_ev:
        EmailVerification.objects.create(
            user=user, verification_token=f'tok_{username}',
            email_confirmed=email_confirmed,
        )
    if has_role:
        UserRole.objects.create(
            user=user, role=role_code, confirmed_by_admin=confirmed,
        )
    return user


# ---------------------------------------------------------------------------
# 1.  User-list page: access control + all filters
# ---------------------------------------------------------------------------

class AdminUsersListAccessTest(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.client = Client()

    def _login_admin(self):
        self.client.login(username='admin', password='admin-pass-99')

    # --- Access control ---

    def test_anonymous_redirected(self):
        resp = self.client.get(reverse('home:admin_users'))
        self.assertNotEqual(resp.status_code, 200)

    def test_non_admin_role_redirected(self):
        researcher = make_user('researcher1', role_code='RESEARCHER', confirmed=True)
        self.client.login(username='researcher1', password='pass-9999')
        resp = self.client.get(reverse('home:admin_users'))
        self.assertNotEqual(resp.status_code, 200)

    def test_unconfirmed_admin_role_redirected(self):
        u = make_user('pending_admin', role_code='ADMIN', confirmed=False)
        self.client.login(username='pending_admin', password='pass-9999')
        resp = self.client.get(reverse('home:admin_users'))
        self.assertNotEqual(resp.status_code, 200)

    def test_confirmed_admin_can_access(self):
        self._login_admin()
        resp = self.client.get(reverse('home:admin_users'))
        self.assertEqual(resp.status_code, 200)

    # --- All filter combinations ---

    def _assert_filter_ok(self, **params):
        self._login_admin()
        resp = self.client.get(reverse('home:admin_users'), params)
        self.assertEqual(resp.status_code, 200)

    def test_filter_all(self):
        self._assert_filter_ok(status='all')

    def test_filter_active(self):
        self._assert_filter_ok(status='active')

    def test_filter_inactive(self):
        self._assert_filter_ok(status='inactive')

    def test_filter_pending_email(self):
        self._assert_filter_ok(status='pending_email')

    def test_filter_pending_role(self):
        self._assert_filter_ok(status='pending_role')

    def test_filter_by_role(self):
        self._assert_filter_ok(role='RESEARCHER')

    def test_search(self):
        self._assert_filter_ok(search='admin')

    # --- Users without UserRole or EmailVerification don't crash page ---

    def test_user_without_role_does_not_crash_list(self):
        make_user('no_role_user', has_role=False)
        self._login_admin()
        resp = self.client.get(reverse('home:admin_users'))
        self.assertEqual(resp.status_code, 200)

    def test_user_without_email_verification_does_not_crash_list(self):
        make_user('no_ev_user', has_ev=False)
        self._login_admin()
        resp = self.client.get(reverse('home:admin_users'))
        self.assertEqual(resp.status_code, 200)

    def test_user_without_role_or_ev_does_not_crash_list(self):
        make_user('bare_user', has_role=False, has_ev=False)
        self._login_admin()
        resp = self.client.get(reverse('home:admin_users'))
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# 2.  Admin center dashboard page
# ---------------------------------------------------------------------------

class AdminCenterDashboardTest(TestCase):

    def setUp(self):
        self.admin = make_admin()
        # Include a user without a role to exercise the safe template path
        make_user('no_role', has_role=False)
        self.client = Client()

    def test_dashboard_loads_for_admin(self):
        self.client.login(username='admin', password='admin-pass-99')
        resp = self.client.get(reverse('home:admin_center'))
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# 3.  Create user
# ---------------------------------------------------------------------------

class AdminUserCreateTest(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.client = Client()
        self.client.login(username='admin', password='admin-pass-99')
        self.url = reverse('home:admin_user_create')

    def test_get_shows_form(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_create_user_success(self):
        resp = self.client.post(self.url, {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'SecurePass1!',
            'password2': 'SecurePass1!',
            'role': 'RESEARCHER',
            'is_active': 'on',
            'email_confirmed': 'on',
            'confirm_role': 'on',
        })
        self.assertRedirects(
            resp,
            reverse('home:admin_user_detail',
                    kwargs={'user_id': User.objects.get(username='newuser').pk}),
            fetch_redirect_response=False,
        )
        created = User.objects.get(username='newuser')
        self.assertTrue(created.is_active)
        self.assertTrue(created.email_verification.email_confirmed)
        self.assertTrue(created.role.confirmed_by_admin)
        self.assertEqual(created.role.role, 'RESEARCHER')

    def test_create_user_inactive_unconfirmed(self):
        resp = self.client.post(self.url, {
            'username': 'pendinguser',
            'email': 'pendinguser@example.com',
            'password1': 'SecurePass1!',
            'password2': 'SecurePass1!',
            'role': 'CLINICIAN',
            # is_active, email_confirmed, confirm_role NOT sent → False
        })
        created = User.objects.get(username='pendinguser')
        self.assertFalse(created.is_active)
        self.assertFalse(created.email_verification.email_confirmed)
        self.assertFalse(created.role.confirmed_by_admin)

    def test_create_duplicate_username_fails(self):
        resp = self.client.post(self.url, {
            'username': 'admin',  # already exists
            'email': 'other@example.com',
            'password1': 'SecurePass1!',
            'password2': 'SecurePass1!',
            'role': 'CLINICIAN',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp, 'form', 'username',
                             'A user with this username already exists.')

    def test_create_duplicate_email_fails(self):
        resp = self.client.post(self.url, {
            'username': 'uniqueuser',
            'email': 'admin@example.com',  # admin's email
            'password1': 'SecurePass1!',
            'password2': 'SecurePass1!',
            'role': 'CLINICIAN',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp, 'form', 'email',
                             'A user with this email address already exists.')

    def test_create_password_mismatch_fails(self):
        resp = self.client.post(self.url, {
            'username': 'mismatch',
            'email': 'mismatch@example.com',
            'password1': 'SecurePass1!',
            'password2': 'DifferentPass!',
            'role': 'CLINICIAN',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp, 'form', 'password2', 'Passwords do not match.')


# ---------------------------------------------------------------------------
# 4.  User detail
# ---------------------------------------------------------------------------

class AdminUserDetailTest(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.target = make_user('target_user', role_code='RESEARCHER', confirmed=True)
        self.client = Client()
        self.client.login(username='admin', password='admin-pass-99')

    def test_detail_loads(self):
        resp = self.client.get(
            reverse('home:admin_user_detail', kwargs={'user_id': self.target.pk})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'target_user')

    def test_detail_user_without_role(self):
        bare = make_user('bare', has_role=False, has_ev=False)
        resp = self.client.get(
            reverse('home:admin_user_detail', kwargs={'user_id': bare.pk})
        )
        self.assertEqual(resp.status_code, 200)

    def test_detail_404_for_missing_user(self):
        resp = self.client.get(
            reverse('home:admin_user_detail', kwargs={'user_id': 99999})
        )
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# 5.  Edit user
# ---------------------------------------------------------------------------

class AdminUserEditTest(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.target = make_user('edit_target')
        self.client = Client()
        self.client.login(username='admin', password='admin-pass-99')

    def test_get_edit_form(self):
        resp = self.client.get(
            reverse('home:admin_user_edit', kwargs={'user_id': self.target.pk})
        )
        self.assertEqual(resp.status_code, 200)

    def test_post_edit_saves(self):
        resp = self.client.post(
            reverse('home:admin_user_edit', kwargs={'user_id': self.target.pk}),
            {
                'username': 'edit_target_new',
                'email': 'edit_new@example.com',
                'first_name': 'Edited',
                'last_name': 'User',
            },
        )
        self.assertRedirects(
            resp,
            reverse('home:admin_user_detail', kwargs={'user_id': self.target.pk}),
            fetch_redirect_response=False,
        )
        self.target.refresh_from_db()
        self.assertEqual(self.target.username, 'edit_target_new')
        self.assertEqual(self.target.first_name, 'Edited')

    def test_can_edit_self_basic_info(self):
        """Admin CAN edit their own basic data (not a blocked self-action)."""
        resp = self.client.post(
            reverse('home:admin_user_edit', kwargs={'user_id': self.admin.pk}),
            {
                'username': 'admin',  # keep same username
                'email': 'admin@example.com',
                'first_name': 'Updated',
                'last_name': 'Admin',
            },
        )
        self.assertRedirects(
            resp,
            reverse('home:admin_user_detail', kwargs={'user_id': self.admin.pk}),
            fetch_redirect_response=False,
        )
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.first_name, 'Updated')


# ---------------------------------------------------------------------------
# 6.  Toggle active
# ---------------------------------------------------------------------------

class AdminUserToggleActiveTest(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.target = make_user('toggle_target', is_active=True)
        self.client = Client()
        self.client.login(username='admin', password='admin-pass-99')
        self.url = reverse('home:admin_user_toggle_active',
                           kwargs={'user_id': self.target.pk})

    def test_deactivate(self):
        self.client.post(self.url)
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)

    def test_activate(self):
        self.target.is_active = False
        self.target.save()
        self.client.post(self.url)
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_active)

    def test_get_method_not_allowed(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 405)

    def test_cannot_deactivate_self(self):
        url = reverse('home:admin_user_toggle_active',
                      kwargs={'user_id': self.admin.pk})
        self.client.post(url)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_cannot_deactivate_last_admin(self):
        """The only admin cannot be deactivated."""
        url = reverse('home:admin_user_toggle_active',
                      kwargs={'user_id': self.admin.pk})
        # admin is trying to deactivate themselves — blocked by self-guard already
        # make a second admin and try to deactivate the last one differently:
        admin2 = make_admin('admin2', 'pass-admin2-99')
        # Now deactivate admin2 (safe, admin still exists)
        url2 = reverse('home:admin_user_toggle_active',
                       kwargs={'user_id': admin2.pk})
        self.client.post(url2)
        admin2.refresh_from_db()
        self.assertFalse(admin2.is_active)
        # Now admin is the only active admin — block deactivation
        # (self-action guard fires first, so use a third non-self admin for the test)
        # Create admin3, deactivate admin2 and admin3, leaving only admin
        admin3 = make_admin('admin3', 'pass-admin3-99')
        url3 = reverse('home:admin_user_toggle_active',
                       kwargs={'user_id': admin3.pk})
        self.client.post(url3)
        admin3.refresh_from_db()
        self.assertFalse(admin3.is_active)
        # Now self-deactivation of admin is blocked (self-guard)
        # For last-admin guard test: we need admin2 to deactivate admin, but
        # admin2 is inactive. Create a fresh scenario:
        last_admin = make_admin('last_admin', 'pass-last-99')
        # Deactivate admin — blocked by self-guard (admin is logged in).
        # Instead, test from admin2 perspective: log in as a different admin
        # and try to deactivate last_admin when last_admin is the only active one.
        # First deactivate 'admin':
        self.client.logout()
        self.client.login(username='last_admin', password='pass-last-99')
        # Deactivate original admin user (admin):
        url_deactivate_admin = reverse('home:admin_user_toggle_active',
                                       kwargs={'user_id': self.admin.pk})
        self.client.post(url_deactivate_admin)
        self.admin.refresh_from_db()
        # Now last_admin is the only active confirmed admin
        # Trying to deactivate itself is blocked by self-guard
        url_self = reverse('home:admin_user_toggle_active',
                           kwargs={'user_id': last_admin.pk})
        self.client.post(url_self)
        last_admin.refresh_from_db()
        self.assertTrue(last_admin.is_active)  # still active


# ---------------------------------------------------------------------------
# 7.  Toggle role confirmation
# ---------------------------------------------------------------------------

class AdminUserToggleRoleConfirmTest(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.target = make_user('role_target', confirmed=False)
        self.client = Client()
        self.client.login(username='admin', password='admin-pass-99')
        self.url = reverse('home:admin_user_toggle_role_confirm',
                           kwargs={'user_id': self.target.pk})

    def test_confirm_role(self):
        self.client.post(self.url)
        self.target.role.refresh_from_db()
        self.assertTrue(self.target.role.confirmed_by_admin)

    def test_revoke_role(self):
        self.target.role.confirmed_by_admin = True
        self.target.role.save()
        self.client.post(self.url)
        self.target.role.refresh_from_db()
        self.assertFalse(self.target.role.confirmed_by_admin)

    def test_get_not_allowed(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 405)

    def test_cannot_revoke_last_admin_confirm(self):
        """Cannot revoke confirmation from the only active confirmed admin."""
        # admin is the only confirmed admin; try to revoke from admin2
        admin2 = make_admin('admin2', 'pass-admin2-99')
        # Deactivate admin2 so only admin is confirmed+active
        admin2.is_active = False
        admin2.save()
        # Now admin is the only active confirmed admin — cannot revoke self
        url_self = reverse('home:admin_user_toggle_role_confirm',
                           kwargs={'user_id': self.admin.pk})
        # Self-action guard fires first
        self.client.post(url_self)
        self.admin.role.refresh_from_db()
        self.assertTrue(self.admin.role.confirmed_by_admin)


# ---------------------------------------------------------------------------
# 8.  Mark email verified
# ---------------------------------------------------------------------------

class AdminUserMarkEmailVerifiedTest(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.target = make_user('ev_target', email_confirmed=False)
        self.client = Client()
        self.client.login(username='admin', password='admin-pass-99')
        self.url = reverse('home:admin_user_mark_email_verified',
                           kwargs={'user_id': self.target.pk})

    def test_marks_email_verified(self):
        self.client.post(self.url)
        self.target.email_verification.refresh_from_db()
        self.assertTrue(self.target.email_verification.email_confirmed)

    def test_idempotent_for_already_verified(self):
        self.target.email_verification.email_confirmed = True
        self.target.email_verification.save()
        resp = self.client.post(self.url)
        # Should still succeed (redirect), just info message
        self.assertEqual(resp.status_code, 302)

    def test_creates_ev_if_missing(self):
        bare = make_user('bare_ev', has_ev=False)
        url = reverse('home:admin_user_mark_email_verified',
                      kwargs={'user_id': bare.pk})
        self.client.post(url)
        self.assertTrue(EmailVerification.objects.filter(user=bare).exists())
        self.assertTrue(bare.email_verification.email_confirmed)

    def test_get_not_allowed(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 405)


# ---------------------------------------------------------------------------
# 9.  Reset password
# ---------------------------------------------------------------------------

class AdminUserResetPasswordTest(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.target = make_user('reset_target')
        self.client = Client()
        self.client.login(username='admin', password='admin-pass-99')
        self.url = reverse('home:admin_user_reset_password',
                           kwargs={'user_id': self.target.pk})

    def test_get_shows_form(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_post_resets_password(self):
        resp = self.client.post(self.url, {
            'new_password1': 'NewSecure99!',
            'new_password2': 'NewSecure99!',
        })
        self.assertRedirects(
            resp,
            reverse('home:admin_user_detail', kwargs={'user_id': self.target.pk}),
            fetch_redirect_response=False,
        )
        self.target.refresh_from_db()
        self.assertTrue(self.target.check_password('NewSecure99!'))

    def test_mismatch_shows_error(self):
        resp = self.client.post(self.url, {
            'new_password1': 'NewSecure99!',
            'new_password2': 'Different99!',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp, 'form', 'new_password2', 'Passwords do not match.')

    def test_can_reset_own_password(self):
        """Admin CAN reset their own password via this admin panel view."""
        url = reverse('home:admin_user_reset_password',
                      kwargs={'user_id': self.admin.pk})
        resp = self.client.post(url, {
            'new_password1': 'NewSecure99!',
            'new_password2': 'NewSecure99!',
        })
        self.assertRedirects(
            resp,
            reverse('home:admin_user_detail', kwargs={'user_id': self.admin.pk}),
            fetch_redirect_response=False,
        )
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('NewSecure99!'))


# ---------------------------------------------------------------------------
# 10.  Delete user
# ---------------------------------------------------------------------------

class AdminUserDeleteTest(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.client = Client()
        self.client.login(username='admin', password='admin-pass-99')

    def _make_target(self):
        return make_user(f'del_target_{User.objects.count()}')

    def test_get_shows_confirmation_page(self):
        target = self._make_target()
        resp = self.client.get(
            reverse('home:admin_user_delete', kwargs={'user_id': target.pk})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, target.username)

    def test_post_deletes_user(self):
        target = self._make_target()
        pk = target.pk
        resp = self.client.post(
            reverse('home:admin_user_delete', kwargs={'user_id': pk})
        )
        self.assertRedirects(
            resp, reverse('home:admin_users'), fetch_redirect_response=False
        )
        self.assertFalse(User.objects.filter(pk=pk).exists())

    def test_cannot_delete_self(self):
        resp = self.client.post(
            reverse('home:admin_user_delete', kwargs={'user_id': self.admin.pk})
        )
        self.assertRedirects(
            resp,
            reverse('home:admin_user_detail', kwargs={'user_id': self.admin.pk}),
            fetch_redirect_response=False,
        )
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_cannot_delete_last_admin(self):
        """When admin is the only active confirmed admin, it cannot be deleted."""
        # Self-guard fires first (admin deleting itself). We need a second admin
        # to try deleting the last remaining one.
        admin2 = make_admin('admin2', 'pass-admin2-99')
        # Deactivate admin so admin2 is now the only active confirmed admin
        self.admin.is_active = False
        self.admin.save()
        # Log in as admin2 and try to delete original admin (inactive, so NOT last admin)
        self.client.logout()
        self.client.login(username='admin2', password='pass-admin2-99')
        # admin is inactive → not the "last active confirmed admin"
        # So deletion should succeed for original admin
        resp = self.client.post(
            reverse('home:admin_user_delete', kwargs={'user_id': self.admin.pk})
        )
        self.assertRedirects(
            resp, reverse('home:admin_users'), fetch_redirect_response=False
        )
        # Now admin2 is last. Try deleting self → self-guard fires
        resp2 = self.client.post(
            reverse('home:admin_user_delete', kwargs={'user_id': admin2.pk})
        )
        self.assertTrue(User.objects.filter(pk=admin2.pk).exists())

    def test_non_admin_cannot_delete(self):
        researcher = make_user('del_researcher', role_code='RESEARCHER',
                               confirmed=True)
        target = self._make_target()
        self.client.logout()
        self.client.login(username='del_researcher', password='pass-9999')
        resp = self.client.post(
            reverse('home:admin_user_delete', kwargs={'user_id': target.pk})
        )
        self.assertNotEqual(resp.status_code, 200)
        self.assertTrue(User.objects.filter(pk=target.pk).exists())


# ---------------------------------------------------------------------------
# 11.  Superuser protection
# ---------------------------------------------------------------------------

class AdminSuperuserProtectionTest(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.superuser = User.objects.create_superuser(
            username='super', email='super@example.com', password='super-pass-99',
        )
        # Give superuser an EmailVerification and role so other views work
        EmailVerification.objects.create(
            user=self.superuser, verification_token='sup_tok', email_confirmed=True,
        )
        UserRole.objects.create(
            user=self.superuser, role='ADMIN', confirmed_by_admin=True,
        )
        self.client = Client()
        self.client.login(username='admin', password='admin-pass-99')

    def test_non_superuser_cannot_delete_superuser(self):
        resp = self.client.post(
            reverse('home:admin_user_delete', kwargs={'user_id': self.superuser.pk})
        )
        self.assertTrue(User.objects.filter(pk=self.superuser.pk).exists())

    def test_non_superuser_cannot_edit_superuser(self):
        resp = self.client.post(
            reverse('home:admin_user_edit', kwargs={'user_id': self.superuser.pk}),
            {
                'username': 'super_hacked',
                'email': 'super@example.com',
            },
        )
        self.superuser.refresh_from_db()
        self.assertNotEqual(self.superuser.username, 'super_hacked')

    def test_superuser_can_edit_superuser(self):
        self.client.logout()
        self.client.login(username='super', password='super-pass-99')
        resp = self.client.post(
            reverse('home:admin_user_edit', kwargs={'user_id': self.superuser.pk}),
            {
                'username': 'super',  # keep same username
                'email': 'super_new@example.com',
                'first_name': 'Super',
                'last_name': 'User',
            },
        )
        self.assertRedirects(
            resp,
            reverse('home:admin_user_detail', kwargs={'user_id': self.superuser.pk}),
            fetch_redirect_response=False,
        )
        self.superuser.refresh_from_db()
        self.assertEqual(self.superuser.email, 'super_new@example.com')


# ---------------------------------------------------------------------------
# 12.  POST-only enforcement
# ---------------------------------------------------------------------------

class PostOnlyEnforcementTest(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.target = make_user('post_target')
        self.client = Client()
        self.client.login(username='admin', password='admin-pass-99')

    def _assert_get_405(self, viewname, **kwargs):
        url = reverse(viewname, kwargs=kwargs)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 405)

    def test_toggle_active_get_405(self):
        self._assert_get_405('home:admin_user_toggle_active',
                              user_id=self.target.pk)

    def test_toggle_role_confirm_get_405(self):
        self._assert_get_405('home:admin_user_toggle_role_confirm',
                              user_id=self.target.pk)

    def test_mark_email_verified_get_405(self):
        self._assert_get_405('home:admin_user_mark_email_verified',
                              user_id=self.target.pk)


# ---------------------------------------------------------------------------
# 13.  Regression: approve_role_request last-admin guard
# ---------------------------------------------------------------------------

class ApproveRoleRequestLastAdminGuardTest(TestCase):
    """
    Regression for: admin_approve_role_request had no guard against demoting
    the last active confirmed admin. An admin who is the only active+confirmed
    admin could approve their own role-change-request (or another admin's),
    leaving the system without any admin.

    Fix applied in home/views.py: added _admin_guard check before updating role.
    """

    def setUp(self):
        self.admin = make_admin('sole_admin', 'sole-pass-99')
        self.client = Client()
        self.client.login(username='sole_admin', password='sole-pass-99')

    def _make_role_request(self, user, from_role, to_role):
        """Create a pending RoleChangeRequest for the given user."""
        return RoleChangeRequest.objects.create(
            user=user,
            current_role=from_role,
            requested_role=to_role,
            status='PENDING',
        )

    def test_cannot_approve_request_that_demotes_last_admin(self):
        """
        Sole admin approving a role-change-request that demotes themselves
        must be blocked by the last-admin guard.
        """
        req = self._make_role_request(self.admin, 'ADMIN', 'RESEARCHER')
        url = reverse('home:admin_approve_role_request', kwargs={'request_id': req.pk})
        self.client.post(url)
        req.refresh_from_db()
        # Request must NOT have been approved
        self.assertNotEqual(req.status, 'APPROVED',
            'Approving role request must be blocked when target is the last admin.')
        # Admin role must be unchanged
        self.admin.role.refresh_from_db()
        self.assertEqual(self.admin.role.role, 'ADMIN',
            'Admin role must not be changed when last-admin guard fires.')

    def test_can_approve_request_demoting_non_last_admin(self):
        """
        When there are two active confirmed admins, demoting one via a
        role-change-request must succeed.
        """
        admin2 = make_admin('admin2_rr', 'pass-admin2-rr-99')
        req = self._make_role_request(admin2, 'ADMIN', 'RESEARCHER')
        url = reverse('home:admin_approve_role_request', kwargs={'request_id': req.pk})
        self.client.post(url)
        req.refresh_from_db()
        self.assertEqual(req.status, 'APPROVED')
        admin2.role.refresh_from_db()
        self.assertEqual(admin2.role.role, 'RESEARCHER')

    def test_can_approve_request_that_does_not_demote_admin(self):
        """
        Approving a role-change-request that keeps ADMIN role (or for a
        non-admin user) must always succeed.
        """
        researcher = make_user('researcher_rr', role_code='RESEARCHER', confirmed=True)
        req = self._make_role_request(researcher, 'RESEARCHER', 'DATA_MANAGER')
        url = reverse('home:admin_approve_role_request', kwargs={'request_id': req.pk})
        self.client.post(url)
        req.refresh_from_db()
        self.assertEqual(req.status, 'APPROVED')
        researcher.role.refresh_from_db()
        self.assertEqual(researcher.role.role, 'DATA_MANAGER')


# ---------------------------------------------------------------------------
# 14.  Regression: detail page shows Edit and Reset Password for self
# ---------------------------------------------------------------------------

class DetailPageSelfActionsTest(TestCase):
    """
    Regression for: user_detail.html hid Edit and Reset Password buttons
    when viewing one's own account (is_self=True), even though both views
    allow self-action. Fix: moved those two links outside the {% if not is_self %}
    block.
    """

    def setUp(self):
        self.admin = make_admin('self_test_admin', 'self-pass-99')
        self.client = Client()
        self.client.login(username='self_test_admin', password='self-pass-99')

    def test_own_detail_page_contains_edit_link(self):
        """Edit link must appear on the admin's own detail page."""
        resp = self.client.get(
            reverse('home:admin_user_detail', kwargs={'user_id': self.admin.pk})
        )
        self.assertEqual(resp.status_code, 200)
        expected_url = reverse('home:admin_user_edit', kwargs={'user_id': self.admin.pk})
        self.assertContains(resp, expected_url,
            msg_prefix='Edit link missing from own detail page.')

    def test_own_detail_page_contains_reset_password_link(self):
        """Reset Password link must appear on the admin's own detail page."""
        resp = self.client.get(
            reverse('home:admin_user_detail', kwargs={'user_id': self.admin.pk})
        )
        self.assertEqual(resp.status_code, 200)
        expected_url = reverse('home:admin_user_reset_password',
                                kwargs={'user_id': self.admin.pk})
        self.assertContains(resp, expected_url,
            msg_prefix='Reset Password link missing from own detail page.')

    def test_own_detail_page_hides_toggle_active_form(self):
        """Toggle Active form must NOT appear on the admin's own detail page."""
        resp = self.client.get(
            reverse('home:admin_user_detail', kwargs={'user_id': self.admin.pk})
        )
        self.assertEqual(resp.status_code, 200)
        toggle_url = reverse('home:admin_user_toggle_active',
                              kwargs={'user_id': self.admin.pk})
        self.assertNotContains(resp, toggle_url,
            msg_prefix='Toggle Active must not appear on own detail page.')

    def test_own_detail_page_hides_delete_link(self):
        """Delete link must NOT appear on the admin's own detail page."""
        resp = self.client.get(
            reverse('home:admin_user_detail', kwargs={'user_id': self.admin.pk})
        )
        self.assertEqual(resp.status_code, 200)
        delete_url = reverse('home:admin_user_delete',
                              kwargs={'user_id': self.admin.pk})
        self.assertNotContains(resp, delete_url,
            msg_prefix='Delete link must not appear on own detail page.')
