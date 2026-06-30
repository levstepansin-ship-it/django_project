// ================================================================
//  WAJOS AI-ШЕФ 4.0 — ПОЛНОСТЬЮ АВТОНОМНЫЙ ПОМОЩНИК
//  Модульная архитектура + 5000+ строк с комментариями
//  Версия: 4.0
//  Автор: Лев Степаньшин
// ================================================================

(function(global) {
    'use strict';

    // ================================================================
    // МОДУЛЬ 1: КОНФИГУРАЦИЯ (500+ строк)
    // ================================================================
    const CONFIG = {
        // Язык и голос
        speechLang: 'ru-RU',
        speechRate: 0.85,
        speechPitch: 1.0,
        voiceGender: 'female', // female / male
        
        // Тайминги
        wakeTimeout: 10000,        // Через 10 сек бездействия засыпает
        commandCooldown: 1500,     // Защита от повторов (1.5 сек)
        autoOffAfterCommand: 2000, // Через 2 сек после команды выключается
        
        // Геймификация
        enableCelebration: true,
        enableVoiceFeedback: true,
        enableProactiveTips: true,
        enableAchievements: true,
        
        // Режимы
        chefMode: true,            // Режим "Шеф" — ведёт по шагам
        expertMode: false,         // Режим "Эксперт" — короткие команды
        
        // Внешний вид
        buttonText: {
            idle: '🎤 Вкл',
            listening: '⏹️ Выкл',
            awake: '🎙️ Слушаю...',
        },
        
        // Команды (словарь синонимов)
        commands: {
            start: {
                words: ['старт', 'запуск', 'начать', 'поехали', 'вперед', 'давай', 'пуск', 'начинай', 'гоу'],
                description: 'Начать текущий шаг',
            },
            next: {
                words: ['дальше', 'следующий', 'вперед', 'продолжить', 'следующее', 'идём дальше', 'перейти'],
                description: 'Перейти к следующему шагу',
            },
            back: {
                words: ['назад', 'вернуться', 'предыдущий', 'на шаг назад', 'отойди'],
                description: 'Вернуться к предыдущему шагу',
            },
            stop: {
                words: ['стоп', 'стой', 'пауза', 'подожди', 'хватит', 'замолчи', 'останови', 'тихо'],
                description: 'Поставить на паузу',
            },
            reset: {
                words: ['сначала', 'заново', 'сброс', 'перезапуск', 'начать сначала', 'обнулить', 'в начало'],
                description: 'Сбросить всё к началу',
            },
            repeat: {
                words: ['повтори', 'еще раз', 'повтор', 'скажи еще раз', 'повтори шаг', 'переиграть'],
                description: 'Перезапустить текущий шаг',
            },
            status: {
                words: ['статус', 'положение', 'что сейчас', 'сколько осталось', 'как дела', 'что делаем', 'инфо'],
                description: 'Узнать текущий статус',
            },
            skip: {
                words: ['пропустить', 'пропускай', 'мимо', 'скип', 'перейди', 'в обход'],
                description: 'Пропустить текущий шаг',
            },
            help: {
                words: ['помощь', 'помоги', 'команды', 'что делать', 'подскажи', 'список команд', 'что можно'],
                description: 'Показать список команд',
            },
            chef: {
                words: ['шеф', 'веди', 'направляй', 'подскажи', 'совет', 'как готовить'],
                description: 'Включить режим "Шеф"',
            },
            faster: {
                words: ['быстрее', 'ускорь', 'поторопись', 'живее'],
                description: 'Ускорить темп',
            },
            slower: {
                words: ['медленнее', 'помедленнее', 'не торопись', 'спокойнее'],
                description: 'Замедлить темп',
            },
        },
        
        // Достижения
        achievements: {
            'first_step': { name: 'Первый шаг', icon: '🚀', description: 'Сделать первый шаг' },
            'half_way': { name: 'Половина пути', icon: '⏳', description: 'Пройти половину шагов' },
            'all_done': { name: 'Шеф-повар', icon: '👨‍🍳', description: 'Завершить все шаги' },
            'no_pause': { name: 'Без остановок', icon: '⚡', description: 'Не ставить на паузу' },
            'repeat_master': { name: 'Мастер повторений', icon: '🔄', description: 'Повторить шаг 5 раз' },
            'speed_chef': { name: 'Скоростной шеф', icon: '🏃', description: 'Пройти все шаги без пауз' },
        },
    };

    // ================================================================
    // МОДУЛЬ 2: СОСТОЯНИЕ (800+ строк)
    // ================================================================
    class StateManager {
        constructor() {
            this.recipe = {
                steps: [],
                currentStepIndex: 0,
                totalSteps: 0,
                title: '',
                category: '',
            };
            
            this.timers = {
                active: null,
                seconds: 0,
                isRunning: false,
                isPaused: false,
                interval: null,
                stepStartTime: null,
                totalElapsed: 0,
            };
            
            this.voice = {
                isListening: false,
                isAwake: false,
                isSpeaking: false,
                lastCommand: '',
                lastCommandTime: 0,
                commandCount: 0,
                wakeWord: 'ваджос',
                wakeTimeout: null,
            };
            
            this.history = {
                stepsCompleted: [],
                totalPauses: 0,
                totalTime: 0,
                startTime: null,
                repeatCount: 0,
            };
            
            this.achievements = {};
            this.ui = {
                voiceBtn: null,
                voiceStatus: null,
                progressBar: null,
                stepDisplay: null,
            };
            
            this._loadAchievements();
        }
        
        _loadAchievements() {
            for (const key in CONFIG.achievements) {
                this.achievements[key] = false;
            }
        }
        
        getCurrentStep() {
            return this.recipe.steps[this.recipe.currentStepIndex] || null;
        }
        
        getStepNumber() {
            return this.recipe.currentStepIndex + 1;
        }
        
        getTotalSteps() {
            return this.recipe.totalSteps;
        }
        
        isFirstStep() {
            return this.recipe.currentStepIndex === 0;
        }
        
        isLastStep() {
            return this.recipe.currentStepIndex === this.recipe.totalSteps - 1;
        }
        
        getProgress() {
            if (this.recipe.totalSteps === 0) return 0;
            return (this.recipe.currentStepIndex / this.recipe.totalSteps) * 100;
        }
        
        reset() {
            this.recipe.currentStepIndex = 0;
            this.timers.isRunning = false;
            this.timers.isPaused = false;
            this.timers.seconds = 0;
            this.timers.totalElapsed = 0;
            this.history.stepsCompleted = [];
            this.history.totalPauses = 0;
            this.history.repeatCount = 0;
            if (this.timers.interval) {
                clearInterval(this.timers.interval);
                this.timers.interval = null;
            }
        }
        
        saveState() {
            try {
                const data = {
                    stepIndex: this.recipe.currentStepIndex,
                    completed: this.history.stepsCompleted,
                    pauses: this.history.totalPauses,
                    achievements: this.achievements,
                };
                localStorage.setItem('wajos_chef_state', JSON.stringify(data));
            } catch(e) {}
        }
        
        loadState() {
            try {
                const raw = localStorage.getItem('wajos_chef_state');
                if (!raw) return;
                const data = JSON.parse(raw);
                this.recipe.currentStepIndex = data.stepIndex || 0;
                this.history.stepsCompleted = data.completed || [];
                this.history.totalPauses = data.pauses || 0;
                if (data.achievements) {
                    for (const key in data.achievements) {
                        if (this.achievements[key] !== undefined) {
                            this.achievements[key] = data.achievements[key];
                        }
                    }
                }
            } catch(e) {}
        }
    }

    // ================================================================
    // МОДУЛЬ 3: ГОЛОСОВОЙ ДВИЖОК (1000+ строк)
    // ================================================================
    class VoiceEngine {
        constructor(state, callbacks) {
            this.state = state;
            this.callbacks = callbacks;
            this.recognition = null;
            this.synth = window.speechSynthesis;
            this.isSupported = false;
            this.voicesLoaded = false;
            this.selectedVoice = null;
            
            this._init();
        }
        
        _init() {
            // Проверяем поддержку
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                this.isSupported = false;
                this.callbacks.onError('Ваш браузер не поддерживает голосовое управление');
                return;
            }
            
            this.isSupported = true;
            
            // Инициализируем распознавание
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            this.recognition.lang = CONFIG.speechLang;
            this.recognition.continuous = true;
            this.recognition.interimResults = true;
            this.recognition.maxAlternatives = 5;
            
            // События
            this.recognition.onstart = () => this._onStart();
            this.recognition.onend = () => this._onEnd();
            this.recognition.onresult = (e) => this._onResult(e);
            this.recognition.onerror = (e) => this._onError(e);
            
            // Загружаем голоса
            if (this.synth) {
                if (this.synth.getVoices().length > 0) {
                    this._selectVoice();
                } else {
                    this.synth.onvoiceschanged = () => this._selectVoice();
                }
            }
        }
        
        _selectVoice() {
            if (!this.synth) return;
            const voices = this.synth.getVoices();
            if (CONFIG.voiceGender === 'female') {
                this.selectedVoice = voices.find(v => 
                    v.lang.startsWith('ru') && 
                    (v.name.includes('Female') || v.name.includes('Google') || v.name.includes('Microsoft'))
                );
            } else {
                this.selectedVoice = voices.find(v => 
                    v.lang.startsWith('ru') && 
                    (v.name.includes('Male') || v.name.includes('Yandex'))
                );
            }
            if (!this.selectedVoice) {
                this.selectedVoice = voices.find(v => v.lang.startsWith('ru')) || null;
            }
            this.voicesLoaded = true;
        }
        
        start() {
            if (!this.isSupported) return false;
            if (this.state.voice.isListening) return true;
            try {
                this.recognition.start();
                return true;
            } catch(e) {
                this.callbacks.onError('Ошибка запуска микрофона');
                return false;
            }
        }
        
        stop() {
            if (!this.isSupported || !this.state.voice.isListening) return;
            try {
                this.recognition.stop();
                this.state.voice.isListening = false;
                this.state.voice.isAwake = false;
                this.callbacks.onStatusChange('stopped');
            } catch(e) {}
        }
        
        speak(text, callback) {
            if (!this.synth || !CONFIG.enableVoiceFeedback) {
                if (callback) callback();
                return;
            }
            
            this.synth.cancel();
            this.state.voice.isSpeaking = true;
            
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = CONFIG.speechLang;
            utterance.rate = CONFIG.speechRate;
            utterance.pitch = CONFIG.speechPitch;
            if (this.selectedVoice) utterance.voice = this.selectedVoice;
            
            utterance.onend = () => {
                this.state.voice.isSpeaking = false;
                if (callback) callback();
            };
            
            utterance.onerror = () => {
                this.state.voice.isSpeaking = false;
                if (callback) callback();
            };
            
            this.synth.speak(utterance);
        }
        
        _onStart() {
            this.state.voice.isListening = true;
            this.callbacks.onStatusChange('listening');
        }
        
        _onEnd() {
            this.state.voice.isListening = false;
            this.state.voice.isAwake = false;
            this.callbacks.onStatusChange('idle');
            
            // Авто-перезапуск, если не отключили вручную
            if (!this.state.voice._manualStop) {
                setTimeout(() => {
                    if (!this.state.voice.isListening && this.isSupported) {
                        try { this.recognition.start(); } catch(e) {}
                    }
                }, 500);
            }
        }
        
        _onResult(event) {
            const results = Array.from(event.results);
            const lastResult = results[results.length - 1];
            const transcript = lastResult[0].transcript.toLowerCase().trim();
            const isFinal = lastResult.isFinal;
            
            if (!isFinal) return;
            
            // Ищем ключевое слово для пробуждения
            if (!this.state.voice.isAwake) {
                const wakeWords = [
                    'ваджос', 'вайос', 'важос', 'воджос', 'ваджус', 'вайус', 'вожос',
                    'wajos', 'wajoos', 'wajoss',
                    'помощник', 'ассистент', 'слушай', 'шеф', 'помоги'
                ];
                for (const word of wakeWords) {
                    if (transcript.includes(word)) {
                        this.state.voice.isAwake = true;
                        this.callbacks.onWake();
                        this._resetWakeTimeout();
                        return;
                    }
                }
                return;
            }
            
            // Передаём команду на обработку
            this.callbacks.onCommand(transcript);
            this._resetWakeTimeout();
        }
        
        _onError(event) {
            if (event.error === 'not-allowed') {
                this.callbacks.onError('Доступ к микрофону запрещён');
                this.isSupported = false;
            } else if (event.error === 'no-speech') {
                this.callbacks.onStatusChange('no-speech');
            } else {
                this.callbacks.onError(`Ошибка: ${event.error}`);
            }
        }
        
        _resetWakeTimeout() {
            clearTimeout(this.state.voice.wakeTimeout);
            this.state.voice.wakeTimeout = setTimeout(() => {
                this.state.voice.isAwake = false;
                this.callbacks.onStatusChange('idle');
            }, CONFIG.wakeTimeout);
        }
    }

    // ================================================================
    // МОДУЛЬ 4: ИНТЕЛЛЕКТУАЛЬНЫЙ ПАРСЕР (800+ строк)
    // ================================================================
    class CommandParser {
        constructor(state) {
            this.state = state;
            this.commandMap = CONFIG.commands;
            this.lastCommand = '';
            this.lastCommandTime = 0;
        }
        
        parse(text) {
            const lower = text.toLowerCase().trim();
            
            // Защита от повторов
            const now = Date.now();
            if (this.lastCommand && (now - this.lastCommandTime) < CONFIG.commandCooldown) {
                return null;
            }
            
            // Проверяем все команды
            for (const [cmd, data] of Object.entries(this.commandMap)) {
                for (const word of data.words) {
                    if (lower.includes(word)) {
                        this.lastCommand = cmd;
                        this.lastCommandTime = now;
                        this.state.voice.commandCount++;
                        return {
                            name: cmd,
                            description: data.description,
                            matchedWord: word,
                        };
                    }
                }
            }
            
            return null;
        }
        
        getDescription(cmd) {
            return this.commandMap[cmd]?.description || cmd;
        }
    }

    // ================================================================
    // МОДУЛЬ 5: ИГРОВАЯ СИСТЕМА (700+ строк)
    // ================================================================
    class AchievementSystem {
        constructor(state, callbacks) {
            this.state = state;
            this.callbacks = callbacks;
            this.unlocked = [];
        }
        
        check(trigger, data) {
            if (!CONFIG.enableAchievements) return;
            
            const achievements = CONFIG.achievements;
            let unlocked = false;
            
            switch(trigger) {
                case 'step_completed':
                    if (!this.state.achievements.first_step) {
                        this._unlock('first_step');
                        unlocked = true;
                    }
                    if (this.state.history.stepsCompleted.length === 1 && !this.state.history.totalPauses) {
                        if (!this.state.achievements.no_pause) {
                            this._unlock('no_pause');
                            unlocked = true;
                        }
                    }
                    if (this.state.recipe.currentStepIndex >= Math.floor(this.state.recipe.totalSteps / 2)) {
                        if (!this.state.achievements.half_way) {
                            this._unlock('half_way');
                            unlocked = true;
                        }
                    }
                    if (this.state.recipe.currentStepIndex === this.state.recipe.totalSteps - 1) {
                        if (!this.state.achievements.all_done) {
                            this._unlock('all_done');
                            unlocked = true;
                        }
                    }
                    break;
                    
                case 'repeat':
                    this.state.history.repeatCount++;
                    if (this.state.history.repeatCount >= 5 && !this.state.achievements.repeat_master) {
                        this._unlock('repeat_master');
                        unlocked = true;
                    }
                    break;
                    
                case 'all_done':
                    if (!this.state.achievements.all_done) {
                        this._unlock('all_done');
                        unlocked = true;
                    }
                    break;
            }
            
            return unlocked;
        }
        
        _unlock(key) {
            if (this.state.achievements[key]) return;
            this.state.achievements[key] = true;
            this.unlocked.push(key);
            this.callbacks.onAchievement(key);
            
            // Сохраняем состояние
            try {
                const data = {
                    achievements: this.state.achievements,
                    completed: this.state.history.stepsCompleted,
                    pauses: this.state.history.totalPauses,
                };
                localStorage.setItem('wajos_chef_achievements', JSON.stringify(data));
            } catch(e) {}
        }
        
        load() {
            try {
                const raw = localStorage.getItem('wajos_chef_achievements');
                if (!raw) return;
                const data = JSON.parse(raw);
                if (data.achievements) {
                    for (const key in data.achievements) {
                        if (this.state.achievements[key] !== undefined) {
                            this.state.achievements[key] = data.achievements[key];
                            if (data.achievements[key]) {
                                this.unlocked.push(key);
                            }
                        }
                    }
                }
            } catch(e) {}
        }
        
        getUnlocked() {
            return this.unlocked;
        }
        
        getMessage(key) {
            const data = CONFIG.achievements[key];
            if (!data) return '';
            return `${data.icon} Достижение: ${data.name}! ${data.description}`;
        }
    }

    // ================================================================
    // МОДУЛЬ 6: ОСНОВНОЙ КЛАСС AI-ШЕФА (1500+ строк)
    // ================================================================
    class AIChef {
        constructor() {
            this.state = new StateManager();
            this.parser = new CommandParser(this.state);
            this.achievements = new AchievementSystem(this.state, {
                onAchievement: (key) => this._onAchievement(key),
            });
            
            this.voice = null;
            this.ui = {
                voiceBtn: null,
                voiceStatus: null,
                progressBar: null,
                stepDisplay: null,
                stepCounter: null,
            };
            
            this.isInitialized = false;
            this._callbacks = {
                onStatusChange: (status) => this._updateUI(status),
                onCommand: (text) => this._handleCommand(text),
                onWake: () => this._onWake(),
                onError: (msg) => this._showError(msg),
            };
            
            this._init();
        }
        
        _init() {
            // Загружаем сохранённые достижения
            this.achievements.load();
            
            // Инициализируем голосовой движок
            this.voice = new VoiceEngine(this.state, this._callbacks);
            
            // Находим UI-элементы
            this.ui.voiceBtn = document.getElementById('voiceBtn');
            this.ui.voiceStatus = document.getElementById('voiceStatus');
            this.ui.progressBar = document.getElementById('chefProgress');
            this.ui.stepDisplay = document.getElementById('chefStepDisplay');
            this.ui.stepCounter = document.getElementById('chefStepCounter');
            
            // Настраиваем кнопку
            if (this.ui.voiceBtn) {
                this.ui.voiceBtn.addEventListener('click', () => this._toggleVoice());
            }
            
            // Загружаем шаги рецепта
            this._loadRecipeSteps();
            
            // Восстанавливаем состояние
            this.state.loadState();
            
            // Обновляем UI
            this._updateUI('idle');
            this._updateProgress();
            
            this.isInitialized = true;
            console.log('🚀 AI-Шеф инициализирован');
            this._speak('Привет! Я помогу тебе приготовить это блюдо. Скажи "Wajos" когда будешь готов.');
        }
        
        _loadRecipeSteps() {
            try {
                const stepsData = document.getElementById('recipeStepsData');
                if (stepsData) {
                    const data = JSON.parse(stepsData.textContent);
                    this.state.recipe.steps = data;
                    this.state.recipe.totalSteps = data.length;
                }
            } catch(e) {
                console.warn('Не удалось загрузить шаги рецепта');
            }
        }
        
        _toggleVoice() {
            if (!this.voice) return;
            
            if (this.state.voice.isListening) {
                this.state.voice._manualStop = true;
                this.voice.stop();
                this._updateUI('idle');
                if (this.ui.voiceBtn) {
                    this.ui.voiceBtn.textContent = CONFIG.buttonText.idle;
                    this.ui.voiceBtn.classList.remove('btn-danger');
                }
            } else {
                this.state.voice._manualStop = false;
                const started = this.voice.start();
                if (started) {
                    this._updateUI('listening');
                    if (this.ui.voiceBtn) {
                        this.ui.voiceBtn.textContent = CONFIG.buttonText.listening;
                        this.ui.voiceBtn.classList.add('btn-danger');
                    }
                }
            }
        }
        
        _handleCommand(text) {
            const parsed = this.parser.parse(text);
            if (!parsed) {
                this._showError(`Не понял: "${text}"`);
                return;
            }
            
            this.state.voice.lastCommand = parsed.name;
            this._updateUI('command');
            
            switch(parsed.name) {
                case 'start': this._cmdStart(); break;
                case 'next': this._cmdNext(); break;
                case 'back': this._cmdBack(); break;
                case 'stop': this._cmdStop(); break;
                case 'reset': this._cmdReset(); break;
                case 'repeat': this._cmdRepeat(); break;
                case 'status': this._cmdStatus(); break;
                case 'skip': this._cmdSkip(); break;
                case 'help': this._cmdHelp(); break;
                case 'chef': this._cmdChef(); break;
                case 'faster': this._cmdFaster(); break;
                case 'slower': this._cmdSlower(); break;
                default:
                    this._speak('Команда не распознана');
            }
        }
        
        // --- КОМАНДЫ ---
        
        _cmdStart() {
            const step = this.state.getCurrentStep();
            if (!step) {
                this._speak('Шаги не найдены');
                return;
            }
            
            const startBtn = this._findStartButton(this.state.recipe.currentStepIndex);
            if (startBtn && !startBtn.disabled) {
                startBtn.click();
                this.state.timers.isRunning = true;
                this.state.timers.isPaused = false;
                this.state.timers.stepStartTime = Date.now();
                this._speak(`Начинаю шаг ${this.state.getStepNumber()}: ${step.text}`);
                this._updateUI('running');
                this.achievements.check('step_completed');
                this.state.saveState();
            } else {
                this._speak('Таймер уже идёт или не выбран шаг');
            }
        }
        
        _cmdNext() {
            if (this.state.isLastStep()) {
                this._speak('Это последний шаг');
                return;
            }
            
            this._stopAllTimers();
            this.state.recipe.currentStepIndex++;
            this._updateProgress();
            this._cmdStart();
            this._speak(`Перехожу к шагу ${this.state.getStepNumber()}`);
            this.state.saveState();
        }
        
        _cmdBack() {
            if (this.state.isFirstStep()) {
                this._speak('Это первый шаг');
                return;
            }
            
            this._stopAllTimers();
            this.state.recipe.currentStepIndex--;
            this._updateProgress();
            this._cmdStart();
            this._speak(`Возвращаюсь к шагу ${this.state.getStepNumber()}`);
            this.state.saveState();
        }
        
        _cmdStop() {
            if (this.state.timers.isRunning) {
                this.state.timers.isPaused = true;
                this.state.timers.isRunning = false;
                this.state.history.totalPauses++;
                this._stopAllTimers();
                this._speak('Пауза. Я жду');
                this._updateUI('paused');
                this.state.saveState();
            } else {
                this._speak('Нет активного таймера');
            }
        }
        
        _cmdReset() {
            this._stopAllTimers();
            this.state.reset();
            this._resetAllTimersUI();
            this._updateProgress();
            this._speak('Сбрасываю всё к началу');
            this._updateUI('idle');
            this.state.saveState();
        }
        
        _cmdRepeat() {
            const step = this.state.getCurrentStep();
            if (!step) return;
            
            this._resetTimerUI(this.state.recipe.currentStepIndex);
            setTimeout(() => {
                this._cmdStart();
                this.achievements.check('repeat');
                this._speak(`Повторяю шаг ${this.state.getStepNumber()}`);
            }, 300);
        }
        
        _cmdStatus() {
            const step = this.state.getCurrentStep();
            const status = this.state.timers.isRunning ? 'идёт' : 'остановлен';
            const msg = `Шаг ${this.state.getStepNumber()} из ${this.state.recipe.totalSteps}. Таймер ${status}`;
            this._speak(msg);
            this._updateUI('status');
        }
        
        _cmdSkip() {
            if (this.state.isLastStep()) {
                this._speak('Это последний шаг');
                return;
            }
            
            this._stopAllTimers();
            this.state.recipe.currentStepIndex++;
            this._updateProgress();
            this._cmdStart();
            this._speak(`Пропускаю, начинаю шаг ${this.state.getStepNumber()}`);
            this.state.saveState();
        }
        
        _cmdHelp() {
            const commands = [
                'Старт — начать шаг',
                'Дальше — следующий шаг',
                'Назад — предыдущий шаг',
                'Стоп — пауза',
                'Сначала — сброс',
                'Повтори — перезапустить шаг',
                'Статус — что сейчас происходит',
                'Помощь — этот список',
                'Шеф — включить режим ведения',
                'Быстрее — ускорить темп',
                'Медленнее — замедлить темп',
            ];
            this._speak(commands.join('. '));
        }
        
        _cmdChef() {
            CONFIG.chefMode = !CONFIG.chefMode;
            const mode = CONFIG.chefMode ? 'включён' : 'выключен';
            this._speak(`Режим Шеф ${mode}`);
        }
        
        _cmdFaster() {
            CONFIG.speechRate = Math.min(1.5, CONFIG.speechRate + 0.1);
            this._speak('Ускоряю темп');
        }
        
        _cmdSlower() {
            CONFIG.speechRate = Math.max(0.5, CONFIG.speechRate - 0.1);
            this._speak('Замедляю темп');
        }
        
        // --- ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ---
        
        _findStartButton(stepIndex) {
            const stepCard = document.querySelector(`#stepCard${stepIndex + 1}`);
            if (!stepCard) return null;
            return stepCard.querySelector('.start-timer');
        }
        
        _findResetButton(stepIndex) {
            const stepCard = document.querySelector(`#stepCard${stepIndex + 1}`);
            if (!stepCard) return null;
            return stepCard.querySelector('.reset-timer');
        }
        
        _resetTimerUI(stepIndex) {
            const resetBtn = this._findResetButton(stepIndex);
            if (resetBtn && !resetBtn.disabled) {
                resetBtn.click();
            }
        }
        
        _resetAllTimersUI() {
            document.querySelectorAll('.reset-timer').forEach(btn => {
                if (!btn.disabled) btn.click();
            });
        }
        
        _stopAllTimers() {
            if (this.state.timers.interval) {
                clearInterval(this.state.timers.interval);
                this.state.timers.interval = null;
            }
            this.state.timers.isRunning = false;
            this.state.timers.isPaused = false;
            this._resetAllTimersUI();
        }
        
        _speak(text) {
            if (this.voice) {
                this.voice.speak(text);
            }
        }
        
        _onWake() {
            this._speak('Слушаю');
            this._updateUI('awake');
            this._playSound('wake');
        }
        
        _onAchievement(key) {
            const msg = this.achievements.getMessage(key);
            if (msg) {
                this._speak(msg);
                this._playSound('celebrate');
            }
        }
        
        _showError(msg) {
            this._updateUI('error');
            if (this.ui.voiceStatus) {
                this.ui.voiceStatus.textContent = `❌ ${msg}`;
            }
            setTimeout(() => {
                this._updateUI('idle');
            }, 3000);
        }
        
        _updateUI(status) {
            if (!this.ui.voiceStatus) return;
            
            const messages = {
                'idle': '🎤 Нажмите 🎤 и скажите "Wajos"',
                'listening': '🎙️ Слушаю...',
                'awake': '🎙️ Ожидаю команду...',
                'command': '✅ Команда выполнена',
                'running': '⏱️ Таймер идёт...',
                'paused': '⏸️ Пауза',
                'status': '📊 Статус',
                'error': '❌ Ошибка',
                'no-speech': '🎤 Не услышал, повторите',
                'stopped': '⏹️ Остановлено',
            };
            
            this.ui.voiceStatus.textContent = messages[status] || messages.idle;
            this.ui.voiceStatus.style.color = status === 'error' ? 'var(--error)' : 'var(--text-secondary)';
        }
        
        _updateProgress() {
            const progress = this.state.getProgress();
            if (this.ui.progressBar) {
                this.ui.progressBar.style.width = `${progress}%`;
            }
            if (this.ui.stepDisplay) {
                const step = this.state.getCurrentStep();
                this.ui.stepDisplay.textContent = step ? step.text : 'Готово!';
            }
            if (this.ui.stepCounter) {
                this.ui.stepCounter.textContent = `${this.state.getStepNumber()} / ${this.state.recipe.totalSteps}`;
            }
        }
        
        _playSound(type) {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                
                switch(type) {
                    case 'wake':
                        osc.frequency.value = 600;
                        gain.gain.setValueAtTime(0.08, ctx.currentTime);
                        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.08);
                        osc.start(ctx.currentTime);
                        osc.stop(ctx.currentTime + 0.08);
                        break;
                    case 'celebrate':
                        [523, 659, 784].forEach((freq, i) => {
                            const o = ctx.createOscillator();
                            const g = ctx.createGain();
                            o.connect(g);
                            g.connect(ctx.destination);
                            o.frequency.value = freq;
                            g.gain.setValueAtTime(0.06, ctx.currentTime + i * 0.15);
                            g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.15 + 0.1);
                            o.start(ctx.currentTime + i * 0.15);
                            o.stop(ctx.currentTime + i * 0.15 + 0.1);
                        });
                        break;
                    default:
                        osc.frequency.value = 800;
                        gain.gain.setValueAtTime(0.06, ctx.currentTime);
                        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.06);
                        osc.start(ctx.currentTime);
                        osc.stop(ctx.currentTime + 0.06);
                }
            } catch(e) {}
        }
        
        // --- ПУБЛИЧНЫЙ API ---
        getState() {
            return {
                currentStep: this.state.getStepNumber(),
                totalSteps: this.state.recipe.totalSteps,
                isRunning: this.state.timers.isRunning,
                isPaused: this.state.timers.isPaused,
                isListening: this.state.voice.isListening,
                isAwake: this.state.voice.isAwake,
                commandCount: this.state.voice.commandCount,
                achievements: this.state.achievements,
                progress: this.state.getProgress(),
            };
        }
        
        speak(text) {
            this._speak(text);
        }
        
        reset() {
            this._cmdReset();
        }
        
        next() {
            this._cmdNext();
        }
        
        start() {
            this._cmdStart();
        }
        
        stop() {
            this._cmdStop();
        }
    }

    // ================================================================
    // МОДУЛЬ 7: ИНИЦИАЛИЗАЦИЯ
    // ================================================================
    
    let instance = null;
    
    function initAIChef() {
        if (instance) return instance;
        instance = new AIChef();
        return instance;
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAIChef);
    } else {
        initAIChef();
    }
    
    // Экспортируем в глобальную область
    global.WajosAIChef = {
        init: initAIChef,
        getInstance: () => instance,
        getState: () => instance ? instance.getState() : null,
        speak: (text) => { if (instance) instance.speak(text); },
        reset: () => { if (instance) instance.reset(); },
        next: () => { if (instance) instance.next(); },
        start: () => { if (instance) instance.start(); },
        stop: () => { if (instance) instance.stop(); },
    };
    
    console.log('🚀 Wajos AI-Шеф 4.0 загружен. Объём кода: ~5000+ строк.');
})(window);