from app import app
from flask import jsonify
from models import *

@app.route('/api/guideline/<int:id>')
def api_get_guideline(id):
    guideline = Guideline.query.get_or_404(id)
    return jsonify({
        "guidelineID": guideline.guidelineID,
        "title": guideline.title,
        "description": guideline.description,
        "seco_processes": [{"description": p.description} for p in guideline.seco_processes],
        "seco_dimensions": [{"name": d.name} for d in guideline.seco_dimensions],
        "conditioning_factors": [{"description": cf.description} for cf in guideline.conditioning_factors],
        "dx_factors": [{"description": f.description} for f in guideline.dx_factors],
        "key_success_criteria": [
            {
                "title": k.title,
                "description": k.description,
                "examples": [{"description": e.description} for e in k.examples]
            }
            for k in guideline.key_success_criteria
        ]
    })