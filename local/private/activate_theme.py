import sys
sys.path.insert(0,'/opt/CTFd')
from CTFd import create_app
from CTFd.utils import set_config
app=create_app()
with app.app_context():
    set_config('ctf_theme','northstar')
    set_config('ctf_name','The Last Backup')
    print('Northstar theme activated; challenge data and scores preserved.')
