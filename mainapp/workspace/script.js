const minutesLabel = document.getElementById('minutes');
const secondsLabel = document.getElementById('seconds');
const startButton = document.getElementById('start');
const pauseButton = document.getElementById('pause');
const resetButton = document.getElementById('reset');

let totalSeconds = 25 * 60;
let interval;

function updateTimer() {
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;

    minutesLabel.textContent = String(minutes).padStart(2, '0');
    secondsLabel.textContent = String(seconds).padStart(2, '0');

    if (totalSeconds <= 0) {
        clearInterval(interval);
        alert('Pomodoro finished!');
        resetTimer();
    }

    totalSeconds--;
}

function startTimer() {
    if (!interval) {
        interval = setInterval(updateTimer, 1000);
    }
}

function pauseTimer() {
    clearInterval(interval);
    interval = null;
}

function resetTimer() {
    clearInterval(interval);
    interval = null;
    totalSeconds = 25 * 60;
    updateTimer();
}

startButton.addEventListener('click', startTimer);
pauseButton.addEventListener('click', pauseTimer);
resetButton.addEventListener('click', resetTimer);

updateTimer(); // Initial display