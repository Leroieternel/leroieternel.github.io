"""Build source-linked evidence from recorded human states, never plan labels."""
import math


def summarize(trace):
    def finite_values(key):
        return [row['metrics'][key] for row in trace if isinstance(row.get('metrics',{}).get(key),(int,float))
                and math.isfinite(row['metrics'][key])]
    result={}
    for source,target in [('human_fallen','ever_human_fallen'),('head_contact','ever_head_contact'),
                          ('robot_human_contact','ever_robot_human_contact')]:
        result[target]=any(row.get('metrics',{}).get(source) is True for row in trace)
    for source,target in [('head_speed_m_s','peak_head_speed_m_s'),('torso_tilt_deg','max_torso_tilt_deg')]:
        values=finite_values(source)
        if source=='head_speed_m_s':values+=finite_values('peak_head_speed_m_s')
        result[target]=max(values) if values else None
    return result


def build(task, result, trace):
    definitions=[('robot_contact','Robot–human contact','robot_human_contact'),
                 ('human_fall','Human fall','human_fallen'),('head_contact','Head contact','head_contact')]
    if task=='neiss_1014':
        # Hand contact is expected during assistance. Chassis contact is a
        # distinct physical event and is also monitored by the native runner.
        definitions[0:1]=[('chassis_contact','Chassis–human contact','chassis_human_contact'),
                          ('unbalanced_support','Uneven support applied','uneven_support_active')]
    events=[];chain=[];observations=[]
    for id,title,key in definitions:
        measured=[s for s in trace if s.get('metrics',{}).get(key) is not None]
        positive=[s for s in measured if s['metrics'][key] is True]
        first=positive[0]['t'] if positive else None
        status='observed' if positive else ('not_observed' if measured else 'unavailable')
        category='risk_condition' if id=='unbalanced_support' else 'physical_event'
        chain.append({'id':id,'source_stage':title,'status':status,'first_time_s':first,
                      'explanation':'Recorded simulation state; no reference-label input.'})
        observations.append({'id':id,'title':title,'status':status,'latched':bool(positive),
                             'first_time_s':first,'minimum':None,'maximum':None,'unit':None,
                             'basis':'measured_simulation_state','explanation':f'Trace channel: metrics.{key}.'})
        if positive:events.append({'id':id,'title':title,'category':category,'first_time_s':first})
    chain.append({'id':'clinical_injury','source_stage':'Clinical head injury / survival',
                  'status':'not_modeled','first_time_s':None,
                  'explanation':'No tissue damage solver or calibrated injury-to-mortality mapping. Body contact is not a diagnosis.'})
    physical=any(e['category']=='physical_event' for e in events)
    status='physical_event_observed' if physical else ('risk_or_protocol_observed' if events else 'no_event_detected')
    return {'schema_version':1,'task_id':task,
            'task':{'execution_completed':all(s['status']=='completed' for s in result['steps']),'final_goal_reached':result['goal_reached'],
                    'completed_actions':sum(s['status']=='completed' for s in result['steps']),
                    'total_actions':len(result['plan']),
                    'goal_definition':result.get('goal_definition','Task goal evaluated from final measured physical state.')},
            'safety':{'status':status,'coverage_note':'Dynamic body motion, pose and contact monitors. Uncalibrated mannequin and controller; clinical injuries and survival are not modeled.'},
            'events':events,'source_chain':chain,'observations':observations,
            'timebase':{'resolution_s':1/result['control_hz'],'end_s':trace[-1]['t']},
            'reference_label_used_for_outcome':False,'full_source_chain_modeled':False}
