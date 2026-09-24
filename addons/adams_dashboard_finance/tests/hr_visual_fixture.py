"""Approved, synthetic HR presentation responses. Imported only by native tests."""
import json
from pathlib import Path


def hr_fixture(catalog):
    data=json.loads(Path(__file__).with_name('hr_reference_fixture.json').read_text())
    assert data['source_sha256']=='36ec95831f3f1e82e0709594d5c177938e3b3805ccd763b1e59c13933b2d7f4a'
    tr=lambda value:catalog.get(value,value)
    people=[e for e in data['employees'] if e['company']=='adams']
    departments=['Sales','Retail','Warehouse','Administration']
    def employee(e):
        return {'id':e['id'],'name':e['name'],'active':e['active'],'job_id':[e['id'],tr(e['job'])],
            'department_id':[departments.index(e['department'])+1,tr(e['department'])],
            'work_location_id':[e['id'],tr(e['location'])],'parent_id':[100,e['manager']],
            'work_email':e['email'],'resource_calendar_id':[1,tr('Standard workweek')]}
    employees={e['id']:employee(e) for e in people}
    def work(row):
        e=employees.get(row.get('employee'))
        return {'employee_id':[e['id'],e['name']] if e else False,'job_id':e['job_id'] if e else False,
            'work_location_id':e['work_location_id'] if e else False,'department_id':e['department_id'] if e else False}
    attendance=[{'id':i+1,**work(r),'check_in_label':r['date']+' '+r['checkIn'],
        'check_out_label':r['date']+' '+r['checkOut'] if r['checkOut'] else '',
        'worked_hours':r['hours'],'status':'closed' if r['checkOut'] else 'open'}
        for i,r in enumerate(data['attendance']) if r['employee'] in employees]
    time_off=[{'id':i+1,**work(r),'date_from_label':r['from']+' 00:00','date_to_label':r['to']+' 23:59',
        'holiday_status_id':[1,tr(r['type'])],'duration':r['duration'],'duration_unit':r['unit'],
        'state':{'Approved':'validate','To approve':'confirm','Refused':'refuse'}[r['status']],
        'state_label':tr(r['status'])} for i,r in enumerate(data['time_off']) if r['employee'] in employees]
    shifts=[{'id':i+1,**work(r),'resource_id':[r['employee'],'Employee'] if r['employee'] else False,
        'role_id':[i+1,r['role']],'start_datetime_label':r['start'].replace('T',' '),
        'end_datetime_label':r['end'].replace('T',' '),'allocated_hours':r['hours'],
        'assigned':bool(r['employee']),'state':r['status'].lower(),'state_label':tr(r['status'])}
        for i,r in enumerate(data['shifts']) if r['company']=='adams']
    def response(tab,filters,offset,size,company_id):
        start,end=filters.get('date_from','2026-09-21'),filters.get('date_to','2026-09-27')
        base={'status':'ready','company_id':company_id,'timezone':'Africa/Cairo','today':'2026-09-22',
            'date_from':start,'date_to':end,'generated_at':'2026-09-22 12:30:00','digits':2,'rows':[],
            'page_size':size,'offset':0,'total':0,'has_more':False,'date_basis':'period'}
        if tab=='overview':
            metrics=[{'key':key,'status':'ready','value':value,'unit':'count','tab':view,'filters':selected}
                for key,value,view,selected in [('employees',17,'employees',{}),('checked_in',len({r['employee_id'][0] for r in attendance if r['status']=='open'}),'attendance',{'scope':'current','status':'open'}),
                ('time_off',2,'time_off',{'scope':'today','status':'validate'}),('unassigned_shifts',2,'shifts',{'status':'published','assignment':'unassigned'})]]
            requests=[r for r in time_off if r['state'] in ('confirm','validate') and r['date_from_label'][:10]<=end and r['date_to_label'][:10]>=start]
            published=[r for r in shifts if r['state']=='published']
            return {**base,'metrics':metrics,'departments':[{'id':i+1,'name':tr(name),'count':len([e for e in people if e['active'] and e['department']==name])} for i,name in enumerate(departments)],
                'attendance_summary':{'no_check_in_today':{'status':'ready','value':2,'tab':'employees','filters':{'scope':'no_check_in_today'}}},
                'previews':{'requests':{'status':'ready','rows':requests[:4],'filters':{'status':'all'}},
                    'published':{'status':'ready','rows':published[:4],'filters':{'status':'published'}}}}
        rows=list({'employees':list(employees.values()),'attendance':attendance,'time_off':time_off,'shifts':shifts}[tab])
        if tab=='employees':rows=[r for r in rows if r['active'] or filters.get('status') in ('all','archived')]
        if tab=='attendance':rows=[r for r in rows if start<=r['check_in_label'][:10]<=end]
        if tab in ('time_off','shifts'):
            a,b=('date_from_label','date_to_label') if tab=='time_off' else ('start_datetime_label','end_datetime_label')
            rows=[r for r in rows if r[a][:10]<=end and r[b][:10]>=start]
        status=filters.get('status','all')
        if status!='all':
            rows=[r for r in rows if (('active' if r.get('active') else 'archived') if tab=='employees' else r.get('state',r.get('status')))==status]
        if filters.get('search'):rows=[]
        total=len(rows);offset=min(offset,((total-1)//size)*size) if total else 0
        return {**base,'status':'ready' if total else 'empty','rows':rows[offset:offset+size],
            'offset':offset,'total':total,'has_more':offset+size<total}
    def profile(employee_id,company_id):
        current=[r for r in attendance if r['employee_id'][0]==employee_id and r['status']=='open']
        upcoming=[r for r in shifts if r.get('employee_id') and r['employee_id'][0]==employee_id and r['state']=='published' and r['end_datetime_label']>'2026-09-22 15:30']
        leave=[r for r in time_off if r['employee_id'][0]==employee_id and r['state']=='validate' and r['date_to_label']>='2026-09-22']
        return {'status':'ready','company_id':company_id,'today':'2026-09-22','employee':employees[employee_id],
            'summaries':[{'tab':tab,'status':'ready'} for tab in ('attendance','time_off','shifts')],
            'snapshots':{tab:{'status':'ready' if rows else 'empty','rows':rows,'total':len(rows)}
                for tab,rows in [('attendance',current[:1]),('shifts',sorted(upcoming,key=lambda r:r['start_datetime_label'])[:1]),('time_off',leave)]}}
    return response,profile
