import json,sys
sys.path.insert(0,'/opt/CTFd')
from CTFd import create_app
from CTFd.models import Users,Challenges,Hints,Solves,Unlocks
app=create_app()
with app.app_context():
    users=Users.query.filter(Users.name.like('full-test-%')).order_by(Users.id).all()
    data={'users':Users.query.count(),'challenges':Challenges.query.count(),'hints':Hints.query.count(),'solves':Solves.query.count(),'unlocks':Unlocks.query.count(),'test_scores':{u.name:u.get_score(admin=True) for u in users}}
    print('STATE_JSON:'+json.dumps(data,sort_keys=True))
