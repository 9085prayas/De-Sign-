from flask import Flask, request, jsonify, g
from flask_cors import CORS
import os
import uuid
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables at the very beginning
load_dotenv()

# Add the project's root directory to the Python path
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auth.descope_auth import require_auth
from workflow import DocumentWorkflow, WorkflowState

# Initialize Flask App
app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize the workflow manager
workflow_manager = DocumentWorkflow()

@app.route('/workflow/start', methods=['POST'])
@require_auth(permission='upload_file')
def start_workflow_route():
    """
    A single endpoint to handle file upload, risk assessment (Agent B),
    and the start of the document processing workflow.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected for upload'}), 400

    session_id = str(uuid.uuid4())
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{filename}")
    
    try:
        file.save(file_path)

        # Prepare the initial state for the workflow
        initial_state = WorkflowState(
            session_id=session_id,
            user_id=g.current_user['user_id'],
            file_path=file_path,
            filename=filename,
        )

        # Start the workflow. It will automatically run Agent B first.
        result = workflow_manager.start_workflow(initial_state)
        
        return jsonify(result)

    except Exception as e:
        # Clean up the saved file if an error occurs
        if os.path.exists(file_path):
            os.remove(file_path)
        print(f"Error during workflow start: {e}")
        return jsonify({'error': 'Failed to start workflow'}), 500

@app.route('/workflow/continue', methods=['POST'])
@require_auth()
def continue_workflow_route():
    """Provides human input to a paused workflow."""
    data = request.get_json()
    session_id = data.get('session_id')
    human_input = data.get('human_input')

    if not session_id or human_input is None:
        return jsonify({'error': 'Session ID and human_input are required'}), 400

    try:
        result = workflow_manager.continue_workflow(session_id, human_input)
        return jsonify(result)
    except Exception as e:
        print(f"Error continuing workflow: {e}")
        return jsonify({'error': 'Failed to continue workflow'}), 500

@app.route('/workflow/state/<session_id>', methods=['GET'])
@require_auth(permission='view_status')
def get_workflow_state_route(session_id):
    """Gets the current state of a specific workflow session."""
    try:
        state = workflow_manager.get_workflow_state(session_id)
        if state:
            return jsonify(state)
        else:
            return jsonify({'error': 'Workflow session not found'}), 404
    except Exception as e:
        print(f"Error getting workflow state: {e}")
        return jsonify({'error': 'Failed to retrieve workflow state'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
