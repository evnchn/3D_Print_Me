from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import app
from starlette.middleware.base import BaseHTTPMiddleware
import os
from dotenv import load_dotenv


passwords = {}
load_dotenv()

normal_pw = os.getenv('CREATE_ACCOUNT_NORMAL_PW')
admin_pw = os.getenv('CREATE_ACCOUNT_ADMIN_PW')

if normal_pw:
    passwords['normal'] = normal_pw
if admin_pw:
    passwords['admin'] = admin_pw
priviledged_users = {'admin'}
unrestricted_page_routes = {'/login', '/register'}

admin_only_route_prefix = "/admin"


class AuthMiddleware(BaseHTTPMiddleware):
    """This middleware restricts access to all NiceGUI pages.

    It redirects the user to the login page if they are not authenticated.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith('/_nicegui') or request.url.path in unrestricted_page_routes or request.url.path.startswith('/endpoint'):
            return await call_next(request)

        if not app.storage.user.get('authenticated', False):
            return RedirectResponse('/login')
        
        if request.url.path.startswith(admin_only_route_prefix):
            username = app.storage.user.get('username', '')
            is_admin = app.storage.general.get("user_pw", {}).get(username, {}).get('admin', False)
            if not is_admin:
                return RedirectResponse('/')
            
        return await call_next(request)