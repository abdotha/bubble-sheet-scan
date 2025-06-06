let modelAnswers = null;
let numberOfQuestions = null;

// Model answers form handling
document.getElementById('modelAnswersForm').onsubmit = async (e) => {
    e.preventDefault();
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const numberOfQuestions = document.getElementById('numberOfQuestions').value;
    const modelAnswers = document.getElementById('modelAnswers').value;

    // Reset UI
    loading.style.display = 'block';
    results.innerHTML = '';
    errorAlert.style.display = 'none';

    try {
        const response = await fetch('/upload_model_answers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                number_of_questions: parseInt(numberOfQuestions),
                answers: modelAnswers.split(',').map(a => parseInt(a.trim()))
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to submit model answers');
        }

        const data = await response.json();
        showSuccess('Model answers submitted successfully');
    } catch (error) {
        showError(error.message);
    } finally {
        loading.style.display = 'none';
    }
};

// File input handling
const fileInput = document.getElementById('fileInput');
const selectedFile = document.getElementById('selectedFile');
const errorAlert = document.getElementById('errorAlert');
const modelAnswersForm = document.getElementById('modelAnswersForm');

// File input change handler
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
        resultsHtml += '<thead><tr><th>Question</th><th>Student Answer</th><th>Correct Answer</th><th>Result</th></tr></thead><tbody>';
        
        for (const [question, details] of Object.entries(data.results)) {
            const questionNum = parseInt(question.replace('question_', ''));
            const studentAnswer = details.student_answer ? details.student_answer.join(', ') : 'No Answer';
            const correctAnswer = details.correct_answer;
            const isCorrect = details.is_correct ? '✓' : '✗';
            const rowClass = details.is_correct ? 'table-success' : 'table-danger';

            resultsHtml += `<tr class="${rowClass}">
                <td>${questionNum}</td>
                <td>${studentAnswer}</td>
                <td>${correctAnswer}</td>
                <td>${isCorrect}</td>
            </tr>`;
        }
        
        resultsHtml += '</tbody></table></div>';
        
        // Add summary
        resultsHtml += `<div class="alert alert-info">
            <strong>Score:</strong> ${data.score} out of ${data.total_questions} (${data.percentage}%)
        </div>`;
        
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

function showError(message) {
    errorAlert.textContent = message;
    errorAlert.style.display = 'block';
}

function showSuccess(message) {
    const successAlert = document.createElement('div');
    successAlert.className = 'alert alert-success';
    successAlert.textContent = message;
    document.querySelector('.container').insertBefore(successAlert, errorAlert);
    setTimeout(() => successAlert.remove(), 3000);
} 