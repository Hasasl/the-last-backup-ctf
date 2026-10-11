import sys,json,os
assert os.environ.get('NORTHSTAR_TEST_ENV') == 'isolated'
sys.path.insert(0,'/opt/CTFd')
from CTFd import create_app
from CTFd.models import db,Users,Challenges,Solves
app=create_app()
with app.app_context():
 data=json.load(open('/bootstrap/replay-browser.json'))
 user=Users(name=data['name'],email=data['name']+'@example.test',password=data['password'],verified=True,hidden=True)
 db.session.add(user);db.session.commit()
 for challenge in Challenges.query.all():
  db.session.add(Solves(user_id=user.id,challenge_id=challenge.id,provided='browser fixture',ip='127.0.0.1'))
 db.session.commit()
 print('Isolated browser fixture created.')
