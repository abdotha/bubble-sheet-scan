let modelAnswers = null;
let numberOfQuestions = null;

// Model answers form handling
document.getElementById('modelAnswersForm').onsubmit = async (e) => {
    e.preventDefault();
    const answersInput = document.getElementById('modelAnswers').value;
    numberOfQuestions = parseInt(document.getElementById('numberOfQuestions').value);
    
    try {
        const answers = answersInput.split(',').map(a => parseInt(a.trim()));
        if (answers.length !== numberOfQuestions) {
            throw new Error('Number of answers must match the number of questions');
        }

        const response = await fetch('/upload_model_answers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                number_of_questions: numberOfQuestions,
                answers: answers
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to upload model answers');
        }

        showError('Model answers saved successfully!', 'success');
    } catch (error) {
        showError(error.message);
    }
};

// File input handling
const fileInput = document.getElementById('fileInput');
const selectedFile = document.getElementById('selectedFile');
const errorAlert = document.getElementById('errorAlert');

fileInput.addEventListener('change', function(e) {
    if (this.files.length > 0) {
        selectedFile.textContent = `Selected file: ${this.files[0].name}`;
    } else {
        selectedFile.textContent = '';
    }
});

// Form submission
document.getElementById('uploadForm').onsubmit = async (e) => {
    e.preventDefault();
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const preview = document.getElementById('preview');

    if (!fileInput.files.length) {
        showError('Please select a file');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    // Reset UI
    loading.style.display = 'block';
    results.innerHTML = '';
    preview.style.display = 'none';
    errorAlert.style.display = 'none';

    try {
        const response = await fetch('/evaluate', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to process image');
        }
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }

        // Display evaluation results
        let resultsHtml = '<h2>Evaluation Results</h2>';
        resultsHtml += '<div class="table-responsive"><table class="table table-striped results-table">';
        resultsHtml += '<thead><tr><th>Question</th><th>Student Answer</th><th>Correct Answer</th><th>Status</th></tr></thead><tbody>';
        
        data.evaluation_results.forEach(result => {
            resultsHtml += `<tr class="${result.is_correct ? 'table-success' : 'table-danger'}">
                <td>${result.question}</td>
                <td>${result.student_answer_display}</td>
                <td>${result.correct_answer}</td>
                <td>${result.is_correct ? '✓' : '✗'}</td>
            </tr>`;
        });
        
        resultsHtml += '</tbody></table></div>';
        
        // Add summary
        resultsHtml += `
            <div class="alert alert-info mt-3">
                <h4>Summary</h4>
                <p>Correct Answers: ${data.summary.correct_answers} out of ${data.summary.total_questions}</p>
                <p>Score: ${data.summary.score.toFixed(2)}%</p>
            </div>
        `;
        
        results.innerHTML = resultsHtml;
        
        // Display combined image
        if (data.combined_image) {
            preview.src = data.combined_image + '?t=' + new Date().getTime();
            preview.style.display = 'block';
        }
    } catch (error) {
        showError(error.message);
    } finally {
        loading.style.display = 'none';
    }
};

function showError(message, type = 'danger') {
    errorAlert.className = `alert alert-${type}`;
    errorAlert.textContent = message;
    errorAlert.style.display = 'block';
} 