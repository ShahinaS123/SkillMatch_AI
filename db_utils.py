def save_analysis_record(supabase_client, user_id, jd_text, cv_text, score, matched_skills, missing_skills, report_text):
    """Saves a single analysis to the database and returns the inserted row ID."""
    try:
        response = supabase_client.table("analysis_history").insert({
            "user_id": str(user_id),
            "jd_text": jd_text[:500], 
            "cv_text": cv_text[:500],
            "match_score": score,
            "matched_skills": ", ".join(matched_skills),
            "missing_skills": ", ".join(missing_skills),
            "report_text": report_text
        }).execute()
        
        if response.data:
            return response.data[0]['id']
        return None
    except Exception as e:
        # Raise the error instead of swallowing it, so app.py can show it
        raise Exception(f"Database Error: {e}")

def update_feedback(supabase_client, rating_id, rating_value):
    """Updates the user rating (1 for thumbs up, 0 for thumbs down)."""
    try:
        supabase_client.table("analysis_history").update({"user_rating": rating_value}).eq("id", rating_id).execute()
        return True
    except Exception as e:
        raise Exception(f"Feedback Error: {e}")