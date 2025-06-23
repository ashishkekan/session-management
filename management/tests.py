from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from management.models import Company, UserProfile, Department, SessionTopic, ExternalTopic
from management.forms import CompanyForm, UserCreationForm, UserEditForm # Add other forms as needed

# TODO: Consider using model_bakery or factory_boy for more robust test data creation

class PublicViewsTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_public_landing_page_accessible(self):
        response = self.client.get(reverse('public_home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'public_home.html')

    def test_login_page_accessible(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'session/login.html')


class AuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.super_admin_user = User.objects.create_superuser(username='superadmin', password='password123', email='super@example.com')
        # Company and UserProfile for a Company Admin
        self.company_a = Company.objects.create(name="Test Company A")
        self.company_admin_user = User.objects.create_user(username='companya_admin', password='password123', email='ca@example.com')
        self.company_admin_profile = UserProfile.objects.create(user=self.company_admin_user, company=self.company_a, role='ADMIN')

    def test_super_admin_login_logout(self):
        # Login
        login_response = self.client.post(reverse('login'), {'username': 'superadmin', 'password': 'password123'})
        self.assertRedirects(login_response, reverse('dashboard'))
        self.assertTrue(User.objects.get(username='superadmin').is_authenticated)

        # Access dashboard
        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertEqual(dashboard_response.status_code, 200)

        # Logout
        logout_response = self.client.get(reverse('logout'))
        self.assertRedirects(logout_response, reverse('login'))
        # Check authentication status by trying to access a protected page or checking request.user (harder in direct test client)
        # A simple way is to try accessing dashboard again, should redirect to login
        dashboard_response_after_logout = self.client.get(reverse('dashboard'))
        self.assertRedirects(dashboard_response_after_logout, f"{reverse('login')}?next={reverse('dashboard')}")


    def test_company_admin_login_logout(self):
        login_response = self.client.post(reverse('login'), {'username': 'companya_admin', 'password': 'password123'})
        self.assertRedirects(login_response, reverse('dashboard'))
        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertEqual(dashboard_response.status_code, 200)
        # Check company specific context in dashboard if possible (more complex test)

        logout_response = self.client.get(reverse('logout'))
        self.assertRedirects(logout_response, reverse('login'))


class CompanyCRUDTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.super_admin_user = User.objects.create_superuser(username='superadmin', password='password123')
        self.client.login(username='superadmin', password='password123')

        self.company_a = Company.objects.create(name="Company A")
        self.company_b = Company.objects.create(name="Company B")

    def test_company_list_view_super_admin(self):
        response = self.client.get(reverse('company_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.company_a.name)
        self.assertContains(response, self.company_b.name)

    def test_company_create_view_super_admin(self):
        response = self.client.get(reverse('company_create'))
        self.assertEqual(response.status_code, 200) # GET form

        post_data = {'name': 'New Test Company'} # Add logo if required and handle file uploads
        response = self.client.post(reverse('company_create'), post_data)
        self.assertRedirects(response, reverse('company_list'))
        self.assertTrue(Company.objects.filter(name='New Test Company').exists())

    def test_company_edit_view_super_admin(self):
        response = self.client.get(reverse('company_edit', args=[self.company_a.pk]))
        self.assertEqual(response.status_code, 200)

        post_data = {'name': 'Company A Updated'}
        response = self.client.post(reverse('company_edit', args=[self.company_a.pk]), post_data)
        self.assertRedirects(response, reverse('company_list'))
        self.company_a.refresh_from_db()
        self.assertEqual(self.company_a.name, 'Company A Updated')

    def test_company_delete_view_super_admin(self):
        company_to_delete = Company.objects.create(name="To Be Deleted")
        response = self.client.get(reverse('company_delete', args=[company_to_delete.pk]))
        self.assertEqual(response.status_code, 200) # Confirmation page

        response = self.client.post(reverse('company_delete', args=[company_to_delete.pk]))
        self.assertRedirects(response, reverse('company_list'))
        self.assertFalse(Company.objects.filter(pk=company_to_delete.pk).exists())


# More test classes for User Management, RBAC, Session Management etc. will follow
class UserManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.super_admin_user = User.objects.create_superuser(username='superadmin', password='password123', email='super@example.com')

        self.company_a = Company.objects.create(name="Company A")
        self.company_b = Company.objects.create(name="Company B")

        self.comp_a_admin_user = User.objects.create_user(username='compa_admin', password='password123', email='compa_admin@example.com')
        UserProfile.objects.create(user=self.comp_a_admin_user, company=self.company_a, role='ADMIN')

    def test_super_admin_can_create_user_in_any_company(self):
        self.client.login(username='superadmin', password='password123')
        response = self.client.get(reverse('add_user'))
        self.assertEqual(response.status_code, 200)

        post_data = {
            'username': 'newusertest', 'password': 'password123',
            'first_name': 'New', 'last_name': 'User', 'email': 'newuser@example.com',
            'company': self.company_b.pk, # Super admin assigns to Company B
            'department': '', # Assuming department is not mandatory for this basic test
            'role': 'EMPLOYEE'
        }
        response = self.client.post(reverse('add_user'), post_data)
        if response.status_code == 302: # Successful redirect
            self.assertTrue(User.objects.filter(username='newusertest').exists())
            new_user = User.objects.get(username='newusertest')
            self.assertEqual(new_user.userprofile.company, self.company_b)
            self.assertEqual(new_user.userprofile.role, 'EMPLOYEE')
        else:
            self.fail(f"User creation failed: {response.context['form'].errors.as_text() if response.context else response.content}")


    def test_company_admin_can_create_user_in_their_company(self):
        self.client.login(username='compa_admin', password='password123')
        response = self.client.get(reverse('add_user'))
        self.assertEqual(response.status_code, 200)

        post_data = {
            'username': 'emp_in_compa', 'password': 'password123',
            'first_name': 'Emp', 'last_name': 'One', 'email': 'emp1@compa.example.com',
            # Company field should be hidden and automatically set to company_a for compa_admin
            # 'company': self.company_a.pk, # This would be submitted if not hidden
            'department': '',
            'role': 'EMPLOYEE' # Comp Admin can assign EMPLOYEE
        }
        response = self.client.post(reverse('add_user'), post_data)
        if response.status_code == 302:
            self.assertTrue(User.objects.filter(username='emp_in_compa').exists())
            new_user = User.objects.get(username='emp_in_compa')
            self.assertEqual(new_user.userprofile.company, self.company_a)
            self.assertEqual(new_user.userprofile.role, 'EMPLOYEE')
        else:
            self.fail(f"User creation by Company Admin failed: {response.context['form'].errors.as_text() if response.context else response.content}")

    def test_company_admin_cannot_create_admin_role(self):
        self.client.login(username='compa_admin', password='password123')
        post_data = {
            'username': 'another_admin_test', 'password': 'password123',
            'first_name': 'Attempt', 'last_name': 'Admin', 'email': 'attempt@example.com',
            'role': 'ADMIN' # Company Admin trying to create another Admin
        }
        response = self.client.post(reverse('add_user'), post_data)
        # Expect form to be invalid or error message because Company Admin cannot assign ADMIN role
        self.assertNotEqual(response.status_code, 302) # Should not redirect on success
        self.assertFalse(User.objects.filter(username='another_admin_test').exists())
        # Check for form errors related to the role field or a general permission message
        # This depends on how the form invalidates this attempt.
        # For now, just checking user is not created and it's not a success.


class RBACTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.super_admin = User.objects.create_superuser(username='super', password='password123')

        self.company1 = Company.objects.create(name="Company One")
        self.company2 = Company.objects.create(name="Company Two")

        self.c1_admin = User.objects.create_user(username='c1_admin', password='password123')
        UserProfile.objects.create(user=self.c1_admin, company=self.company1, role='ADMIN')

        self.c1_employee = User.objects.create_user(username='c1_emp', password='password123')
        UserProfile.objects.create(user=self.c1_employee, company=self.company1, role='EMPLOYEE')

    def test_company_admin_can_edit_own_company(self):
        self.client.login(username='c1_admin', password='password123')
        response = self.client.get(reverse('company_edit', args=[self.company1.pk]))
        self.assertEqual(response.status_code, 200)

        post_data = {'name': 'Company One Updated'}
        response = self.client.post(reverse('company_edit', args=[self.company1.pk]), post_data)
        # Company Admin editing their own company should redirect to dashboard.
        # The view currently redirects to company_list if super_admin, else dashboard.
        # This means for a CompanyAdmin, it should go to 'dashboard'.
        # However, the company_edit_view redirects to company_list OR dashboard based on is_super_admin.
        # The current view logic for company_edit_view is:
        # `return redirect("company_list" if is_super_admin(request.user) else "dashboard")`
        # So, for a Company Admin (not super admin), it *should* redirect to 'dashboard'.
        # The original test had `reverse('company_list')` which was based on an outdated assumption.
        # The view's redirect logic for successful company edit is:
        # `messages.success(request, f"Company '{updated_company.name}' updated successfully.")`
        # `return redirect("company_list")` -- THIS IS THE ACTUAL REDIRECT in company_edit_view
        # This redirect in company_edit_view needs to be role-aware.
        # For now, to make the test pass with current view logic, I'll expect company_list,
        # but this highlights a needed view change for better UX for Company Admin.
        # For now, I'll keep it as `company_list` and note this view redirect needs fixing.
        # **Correction**: The view logic IS `redirect("company_list" if is_super_admin(request.user) else "dashboard")`
        # No, looking at `company_edit_view` again, it's `return redirect("company_list")` unconditionally.
        # This needs to be fixed in the view.
        # For this test to pass *now*, I must expect `company_list`.
        # I will fix the view first.

        # **Assuming view is fixed to redirect to dashboard for CompanyAdmin:**
        # self.assertRedirects(response, reverse('dashboard'))

        # View has been fixed to redirect CompanyAdmin to company_detail page.
        self.assertRedirects(response, reverse('company_detail', args=[self.company1.pk]))

        self.company1.refresh_from_db()
        self.assertEqual(self.company1.name, 'Company One Updated')

    def test_company_admin_cannot_edit_other_company(self):
        self.client.login(username='c1_admin', password='password123')
        response = self.client.get(reverse('company_edit', args=[self.company2.pk]))
        self.assertNotEqual(response.status_code, 200) # Should be forbidden or redirect
        # Expecting redirect to dashboard or login if not permitted
        self.assertTrue(response.status_code == 302 or response.status_code == 403)


    def test_employee_cannot_edit_company(self):
        self.client.login(username='c1_emp', password='password123')
        response = self.client.get(reverse('company_edit', args=[self.company1.pk]))
        self.assertNotEqual(response.status_code, 200)
        self.assertTrue(response.status_code == 302 or response.status_code == 403) # Redirect or forbidden

    def test_employee_cannot_access_add_user(self):
        self.client.login(username='c1_emp', password='password123')
        response = self.client.get(reverse('add_user'))
        self.assertNotEqual(response.status_code, 200) # Should redirect
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('dashboard'))) # Redirect to dashboard with message


# This is a starting point. Many more tests are needed for comprehensive coverage.
