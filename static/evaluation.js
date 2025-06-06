let modelAnswers = null;
let numberOfQuestions = null;

// File input handling
const fileInput = document.getElementById('fileInput');
const selectedFile = document.getElementById('selectedFile');
const errorAlert = document.getElementById('errorAlert');
const modelAnswersForm = document.getElementById('modelAnswersForm');
const loading = document.getElementById('loading');
const results = document.getElementById('results');
const preview = document.getElementById('preview');
const uploadForm = document.getElementById('uploadForm');

// File input change handler
fileInput.addEventListener('change', function(e) {
    if (this.files.length > 0) {
        selectedFile.textContent = `Selected file: ${this.files[0].name}`;
    } else {
        selectedFile.textContent = '';
    }
});

// Model answers form submission
modelAnswersForm.onsubmit = async (e) => {
    e.preventDefault();
    
    const numberOfQuestions = document.getElementById('numberOfQuestions').value;
    const modelAnswers = document.getElementById('modelAnswers').value;

    if (!numberOfQuestions || !modelAnswers) {
        showError('Please fill in all fields');
        return;
    }

    // Disable form while processing
    setFormState(false);
    
    // Reset UI
    resetUI();

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
        setFormState(true);
    }
};

// Upload form submission
uploadForm.onsubmit = async (e) => {
    e.preventDefault();
    
    if (!fileInput.files.length) {
        showError('Please select a file first');
        return;
    }

    // Disable form while processing
    setFormState(false);
    
    // Reset UI
    resetUI();

    try {
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

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

        await displayResults(data);
    } catch (error) {
        showError(error.message);
    } finally {
        setFormState(true);
    }
};

async function displayResults(data) {
    // Display results
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
    resultsHtml += `<div class="alert alert-info">
        <strong>Score:</strong> ${data.score} out of ${data.total_questions} (${data.percentage}%)
    </div>`;
    results.innerHTML = resultsHtml;

    // Display combined image if available
    if (data.combined_image) {
        await loadImage(data.combined_image);
    }
}

function loadImage(src) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
            preview.src = src + '?t=' + new Date().getTime();
            preview.style.display = 'block';
            resolve();
        };
        img.onerror = () => {
            showError('Failed to load processed image');
            reject();
        };
        img.src = src;
    });
}

function setFormState(enabled) {
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    submitButtons.forEach(button => button.disabled = !enabled);
    loading.style.display = enabled ? 'none' : 'block';
}

function resetUI() {
    loading.style.display = 'block';
    results.innerHTML = '';
    preview.style.display = 'none';
    errorAlert.style.display = 'none';
}

function showError(message) {
    errorAlert.textContent = message;
    errorAlert.style.display = 'block';
    loading.style.display = 'none';
}

function showSuccess(message) {
    const successAlert = document.createElement('div');
    successAlert.className = 'alert alert-success';
    successAlert.textContent = message;
    document.querySelector('.container').insertBefore(successAlert, errorAlert);
    setTimeout(() => successAlert.remove(), 3000);
} 