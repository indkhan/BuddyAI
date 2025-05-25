const minutesDisplay = document.getElementById('minutes');
const secondsDisplay = document.getElementById('seconds');
const startButton = document.getElementById('start');
const pauseButton = document.getElementById('pause');
const resetButton = document.getElementById('reset');

let timer;
let minutes = 25;
let seconds = 0;
let isPaused = true;

function updateDisplay() {
    minutesDisplay.textContent = String(minutes).padStart(2, '0');
    secondsDisplay.textContent = String(seconds).padStart(2, '0');
}

function startTimer() {
    if (isPaused) {
        isPaused = false;
        timer = setInterval(() => {
            if (seconds === 0) {
                if (minutes === 0) {
                    clearInterval(timer);
                    alert('Pomodoro finished!');
                    resetTimer();
                    return;
                }
                minutes--;
                seconds = 59;
            } else {
                seconds--;
            }
            updateDisplay();
        }, 1000);
    }
}

function pauseTimer() {
    isPaused = true;
    clearInterval(timer);
}

function resetTimer() {
    pauseTimer();
    minutes = 25;
    seconds = 0;
    updateDisplay();
}

startButton.addEventListener('click', startTimer);
pauseButton.addEventListener('click', pauseTimer);
resetButton.addEventListener('click', resetTimer);

updateDisplay();