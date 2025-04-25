SELECT 
    cd.start_time AS collected_data_start_time,
    cd.end_time AS collected_data_end_time,
    
    dq.academic_level AS developer_academic_level,
    dq.previus_xp AS developer_previous_experience,
    dq.emotion AS developer_emotion,
    dq.comments AS developer_comments,
    dq.segment AS developer_segment,
    dq.experience AS developer_experience,
    
    n.action AS navigation_action,
    n.title AS navigation_title,
    n.url AS navigation_url,
    n.timestamp AS navigation_timestamp,
    
    pt.performed_task_id AS performed_task_id,
    pt.initial_timestamp AS performed_task_start_time,
    pt.final_timestamp AS performed_task_end_time,
    pt.status AS performed_task_status,
    
    q.question_id AS question_id,
    q.question AS question_text,
    
    a.answer_id AS answer_id,
    a.answer AS answer_text
FROM 
    collected_data cd
LEFT JOIN developer_questionnaire dq ON cd.collected_data_id = dq.collected_data_id
LEFT JOIN navigation n ON cd.collected_data_id = n.collected_data_id
LEFT JOIN performed_task pt ON cd.collected_data_id = pt.collected_data_id
LEFT JOIN question q ON pt.task_id = q.task_id
LEFT JOIN answer a ON pt.performed_task_id = a.performed_task_id AND q.question_id = a.question_id
WHERE 
    cd.evaluation_id = :evaluation_id;
