import { useEffect, useRef, useState } from 'react'
import {
  Bell, BookOpen, CalendarDays, Check, ClipboardList, Clock3, FileText,
  FolderInput, HelpCircle, LoaderCircle, MessageCircleMore, MonitorUp, RefreshCw,
  Paperclip, Settings, Sparkles, Trophy, UserRound, XCircle,
  Volume2, Languages, Plus, RotateCcw, Trash2,
} from 'lucide-react'
import './App.css'

const navigation = [
  ['同步中心', RefreshCw],
  ['原始消息', FolderInput],
  ['老师要求', ClipboardList],
  ['英语单词', Languages],
  ['作业提醒', Volume2],
  ['老师画像', Sparkles],
  ['表扬档案', Trophy],
  ['设置', Settings],
]

const categoryClass = {
  老师要求: 'teacher',
  作业: 'homework',
  考试提醒: 'exam',
  普通消息: 'ordinary',
}

function formatTime(value) {
  if (!value) return '尚未同步'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  }).format(new Date(value))
}

function StatusDot({ online }) {
  return <span className={`status-dot ${online ? 'online' : 'offline'}`} aria-hidden="true" />
}

function sourceLabel(source) {
  return source === 'qq_group' ? 'QQ' : '微信'
}

function App() {
  const [dashboard, setDashboard] = useState(null)
  const [syncing, setSyncing] = useState(false)
  const [qqSyncing, setQqSyncing] = useState(false)
  const [qqLoginVisible, setQqLoginVisible] = useState(false)
  const [qqLoginStarting, setQqLoginStarting] = useState(false)
  const [qqLoginNonce, setQqLoginNonce] = useState(0)
  const [notice, setNotice] = useState('')
  const [messageType, setMessageType] = useState('全部')
  const [messageSource, setMessageSource] = useState('全部')
  const [teacherName, setTeacherName] = useState('全部')
  const [messageDate, setMessageDate] = useState('')
  const [activeView, setActiveView] = useState('同步中心')
  const [requirementDate, setRequirementDate] = useState('')
  const [selectedHomeworkId, setSelectedHomeworkId] = useState('')
  const [generatingVoice, setGeneratingVoice] = useState(false)
  const [wordForm, setWordForm] = useState({ word: '', meaning: '', error_type: '拼写', source: '听写', note: '' })
  const [wordLibraryMatch, setWordLibraryMatch] = useState(null)
  const [wordLibraryChecking, setWordLibraryChecking] = useState(false)
  const [savingWord, setSavingWord] = useState(false)
  const [quizWords, setQuizWords] = useState([])
  const [quizIndex, setQuizIndex] = useState(0)
  const [englishView, setEnglishView] = useState('词库')
  const [ketQuery, setKetQuery] = useState('')
  const [ketWords, setKetWords] = useState([])
  const [selectedKetWord, setSelectedKetWord] = useState(null)
  const [ketDetail, setKetDetail] = useState(null)
  const [ketLoading, setKetLoading] = useState(false)
  const [memoryInput, setMemoryInput] = useState('')
  const [memoryPlan, setMemoryPlan] = useState(null)
  const [reviewSession, setReviewSession] = useState(false)
  const [reviewSessionWords, setReviewSessionWords] = useState([])
  const [reviewIndex, setReviewIndex] = useState(0)
  const [reviewAnswer, setReviewAnswer] = useState('')
  const [reviewResult, setReviewResult] = useState(null)
  const [reviewMode, setReviewMode] = useState('meaning')
  const [dictationExample, setDictationExample] = useState(null)
  const [dictationExampleLoading, setDictationExampleLoading] = useState(false)
  const [dictationPickerOpen, setDictationPickerOpen] = useState(false)
  const [reviewMeaning, setReviewMeaning] = useState('')
  const [reviewMeaningLoading, setReviewMeaningLoading] = useState(false)
  const [libraryTestSession, setLibraryTestSession] = useState(false)
  const [libraryTestWords, setLibraryTestWords] = useState([])
  const [libraryTestCount, setLibraryTestCount] = useState(35)
  const [libraryTestIndex, setLibraryTestIndex] = useState(0)
  const [libraryTestAnswer, setLibraryTestAnswer] = useState('')
  const [libraryTestResult, setLibraryTestResult] = useState(null)
  const [libraryTestMeaning, setLibraryTestMeaning] = useState('')
  const [libraryTestMeaningLoading, setLibraryTestMeaningLoading] = useState(false)
  const [libraryTestMode, setLibraryTestMode] = useState('meaning')
  const [libraryTestExample, setLibraryTestExample] = useState(null)
  const [libraryTestExampleLoading, setLibraryTestExampleLoading] = useState(false)
  const [libraryTestChoices, setLibraryTestChoices] = useState(null)
  const [libraryTestChoicesLoading, setLibraryTestChoicesLoading] = useState(false)
  const [libraryTestMistakeWord, setLibraryTestMistakeWord] = useState('')
  const [libraryTestScope, setLibraryTestScope] = useState('ket')
  const [selectedMistakeDates, setSelectedMistakeDates] = useState([])
  const [libraryTestStats, setLibraryTestStats] = useState({ correct: 0, incorrect: 0 })
  const [libraryTestSummary, setLibraryTestSummary] = useState(null)
  const libraryTestStatsRef = useRef({ correct: 0, incorrect: 0 })
  const [reviewMistakeDates, setReviewMistakeDates] = useState([])
  const [reviewDictationCount, setReviewDictationCount] = useState(35)
  const [pronunciationAccent, setPronunciationAccent] = useState('us')
  const [pendingDeleteId, setPendingDeleteId] = useState('')

  async function refresh() {
    const response = await fetch('/api/dashboard')
    if (!response.ok) throw new Error('无法读取本地同步状态')
    setDashboard(await response.json())
  }

  useEffect(() => {
    let retryTimer
    const refreshDashboard = async () => {
      try {
        await refresh()
        setNotice('')
      } catch (error) {
        setNotice(error.message)
        retryTimer = window.setTimeout(refreshDashboard, 2000)
      }
    }
    refreshDashboard()
    window.addEventListener('focus', refreshDashboard)
    return () => {
      window.clearTimeout(retryTimer)
      window.removeEventListener('focus', refreshDashboard)
    }
  }, [])

  useEffect(() => {
    if (activeView !== '英语单词' || englishView !== '词库') return
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(`/api/ket-vocabulary?query=${encodeURIComponent(ketQuery)}`)
        const result = await response.json()
        if (response.ok) {
          setKetWords(result.items || [])
          setDashboard((current) => current ? { ...current, ket_library: { ...(current.ket_library || {}), total: result.total } } : current)
        }
      } catch (_) {}
    }, 180)
    return () => window.clearTimeout(timer)
  }, [activeView, englishView, ketQuery])

  useEffect(() => {
    const word = wordForm.word.trim().toLowerCase()
    if (!/^[a-z][a-z'\-]{1,78}$/.test(word)) {
      setWordLibraryMatch(null)
      setWordLibraryChecking(false)
      return undefined
    }
    setWordLibraryChecking(true)
    let active = true
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(`/api/ket-vocabulary?query=${encodeURIComponent(word)}`)
        const result = await response.json()
        if (!response.ok) throw new Error()
        if (active) setWordLibraryMatch((result.items || []).find((item) => item.word.toLowerCase() === word || item.aliases?.includes(word)) || null)
      } catch (_) {
        if (active) setWordLibraryMatch(null)
      } finally {
        if (active) setWordLibraryChecking(false)
      }
    }, 220)
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [wordForm.word])

  useEffect(() => {
    const canAdvanceLibraryTest = libraryTestSession && Boolean(libraryTestResult)
    const canAdvanceReview = reviewSession && Boolean(reviewResult)
    if (!canAdvanceLibraryTest && !canAdvanceReview) return undefined
    const onKeyDown = (event) => {
      if (event.key !== 'Enter' || event.repeat) return
      event.preventDefault()
      if (canAdvanceLibraryTest) advanceLibraryTest()
      else advanceReview()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [libraryTestSession, libraryTestResult, reviewSession, reviewResult, libraryTestIndex, reviewIndex])

  async function startSync() {
    setSyncing(true)
    setNotice(`正在打开微信并读取“${dashboard?.group || '六六班级'}”的可见消息…`)
    try {
      const response = await fetch('/api/sync', { method: 'POST' })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || '同步未完成')
      setDashboard(result.dashboard)
      setNotice(result.message)
    } catch (error) {
      setNotice(error.message)
    } finally {
      setSyncing(false)
    }
  }

  async function startQqSync() {
    if (!dashboard?.qq_ready) {
      await startQqLogin()
      return
    }
    setQqSyncing(true)
    setNotice(`正在读取 QQ 群“${dashboard?.qq_group || '二7班学习交流群'}”…`)
    try {
      const response = await fetch('/api/sync/qq', { method: 'POST' })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'QQ 同步未完成')
      setDashboard(result.dashboard)
      setNotice(result.message)
    } catch (error) {
      setNotice(error.message)
    } finally {
      setQqSyncing(false)
    }
  }

  async function startQqLogin() {
    setQqLoginVisible(true)
    setQqLoginStarting(true)
    setNotice('正在准备 QQ 登录二维码…')
    try {
      const response = await fetch('/api/qq/login/start', { method: 'POST' })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'QQ 登录二维码生成失败')
      setQqLoginNonce(Date.now())
      setNotice('请使用手机 QQ 扫描二维码；扫码后点击“检查 QQ 登录”。')
    } catch (error) {
      setNotice(error.message)
    } finally {
      setQqLoginStarting(false)
    }
  }

  async function checkQqLogin() {
    try {
      const response = await fetch('/api/qq/status')
      const status = await response.json()
      if (!response.ok) throw new Error(status.detail || '无法检查 QQ 登录状态')
      await refresh()
      if (status.ready) setQqLoginVisible(false)
      else setNotice('QQ 还未完成登录，请在手机 QQ 上确认后再检查。')
    } catch (error) {
      setNotice(error.message)
    }
  }

  async function toggleAutomation(enabled) {
    try {
      const response = await fetch('/api/automation', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || '无法更新自动化设置')
      setDashboard(result.dashboard)
      setNotice(result.message)
    } catch (error) {
      setNotice(error.message)
    }
  }

  async function toggleVoiceReminders(enabled) {
    try {
      const response = await fetch('/api/voice-reminders', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || '无法更新语音提醒')
      setDashboard(result.dashboard)
      setNotice(result.message)
    } catch (error) {
      setNotice(error.message)
    }
  }

  async function generateVoiceReminder(messageId) {
    setGeneratingVoice(true)
    try {
      const response = await fetch('/api/voice-reminders/generate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_id: messageId }),
      })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || '无法生成语音提醒')
      setDashboard(result.dashboard)
      setNotice(result.message)
    } catch (error) {
      setNotice(error.message)
    } finally {
      setGeneratingVoice(false)
    }
  }

  async function requestScreenRecording() {
    try {
      const response = await fetch('/api/permissions/request-screen-recording', { method: 'POST' })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || '无法请求系统权限')
      setDashboard(result.dashboard)
      setNotice(result.message)
    } catch (error) {
      setNotice(error.message)
    }
  }

  async function saveWord(event) {
    event.preventDefault()
    setSavingWord(true)
    try {
      const response = await fetch('/api/vocabulary', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...wordForm, ket_word_id: wordLibraryMatch?.id || '' }) })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || '错词保存失败')
      setDashboard(result.dashboard)
      setWordForm({ word: '', meaning: '', error_type: '拼写', source: '听写', note: '' })
      setWordLibraryMatch(null)
      setNotice(result.message)
    } catch (error) {
      setNotice(error.message)
    } finally {
      setSavingWord(false)
    }
  }

  async function reviewWord(wordId, result) {
    try {
      const response = await fetch('/api/vocabulary/review', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ word_id: wordId, result }) })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail || '复习结果保存失败')
      setDashboard(payload.dashboard)
      setNotice(payload.message)
      if (quizWords.length) setQuizIndex((index) => index + 1)
    } catch (error) {
      setNotice(error.message)
    }
  }

  async function deleteWord(word) {
    try {
      const response = await fetch('/api/vocabulary/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ word_id: word.id }) })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || '删除失败')
      setDashboard(result.dashboard)
      setPendingDeleteId('')
      setNotice(result.message)
    } catch (error) {
      setNotice(error.message)
    }
  }

  function requestDelete(word) {
    if (pendingDeleteId === word.id) {
      deleteWord(word)
    } else {
      setPendingDeleteId(word.id)
      setNotice(`再次点击“确认删除”即可移除 ${word.word}。`)
    }
  }

  function startQuiz(size) {
    const candidates = [...(data?.vocabulary?.today || []), ...(data?.vocabulary?.difficult || [])]
    const unique = candidates.filter((word, index) => candidates.findIndex((item) => item.id === word.id) === index).slice(0, size)
    setQuizWords(unique)
    setQuizIndex(0)
  }

  async function selectKetWord(word) {
    setSelectedKetWord(word)
    setKetDetail(null)
    setKetLoading(true)
    try {
      const response = await fetch(`/api/ket-vocabulary/detail?word=${encodeURIComponent(word.word)}`)
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || '单词详情加载失败')
      setKetDetail(result)
    } catch (error) {
      setNotice(error.message)
    } finally {
      setKetLoading(false)
    }
  }

  async function speakWord(word, detail = null, accent = pronunciationAccent) {
    window.speechSynthesis.cancel()
    try {
      const pronunciation = await fetch(`/api/ket-vocabulary/pronunciation?word=${encodeURIComponent(word)}&accent=${accent}`)
      const pronunciationData = await pronunciation.json()
      if (pronunciation.ok && pronunciationData.url) {
        window.__hunterWordAudio?.pause()
        const audio = new Audio(pronunciationData.url)
        window.__hunterWordAudio = audio
        await audio.play()
        return
      }
    } catch (_) {}
    const wordDetail = detail || await fetch(`/api/ket-vocabulary/detail?word=${encodeURIComponent(word)}`).then((response) => response.ok ? response.json() : null).catch(() => null)
    const audioUrl = accent === 'us' ? wordDetail?.audio_us : wordDetail?.audio_uk
    if (audioUrl) {
      window.__hunterWordAudio?.pause()
      const audio = new Audio(audioUrl)
      window.__hunterWordAudio = audio
      audio.play().catch(() => {})
      return
    }
    const utterance = new SpeechSynthesisUtterance(word)
    utterance.lang = accent === 'us' ? 'en-US' : 'en-GB'
    utterance.rate = 0.78
    const locale = accent === 'us' ? 'en-us' : 'en-gb'
    utterance.voice = window.speechSynthesis.getVoices().find((voice) => voice.lang.toLowerCase() === locale) || null
    window.speechSynthesis.speak(utterance)
  }

  async function prepareDictationExample(word, shouldPlay = true, accent = pronunciationAccent) {
    setDictationExample(null)
    setDictationExampleLoading(true)
    try {
      const response = await fetch(`/api/english-practice/dictation-example?word=${encodeURIComponent(word)}&accent=${accent}`)
      const example = await response.json()
      if (!response.ok) throw new Error(example.detail || '例句暂时无法生成')
      setDictationExample(example)
      if (shouldPlay && example.audio_url) {
        window.__hunterWordAudio?.pause()
        const audio = new Audio(example.audio_url)
        window.__hunterWordAudio = audio
        audio.play().catch(() => {})
      }
      return example
    } catch (error) {
      setNotice(error.message)
      return null
    } finally {
      setDictationExampleLoading(false)
    }
  }

  function replayDictationExample(useAlternateAccent = false) {
    const current = reviewSessionWords[reviewIndex]
    const accent = useAlternateAccent ? (pronunciationAccent === 'us' ? 'uk' : 'us') : pronunciationAccent
    if (!useAlternateAccent && dictationExample?.audio_url) {
      window.__hunterWordAudio?.pause()
      const audio = new Audio(dictationExample.audio_url)
      window.__hunterWordAudio = audio
      audio.play().catch(() => {})
      return
    }
    if (current) prepareDictationExample(current.word, true, accent)
  }

  async function prepareReviewMeaning(word, knownMeaning = '') {
    if (knownMeaning) {
      setReviewMeaning(knownMeaning)
      setReviewMeaningLoading(false)
      return
    }
    setReviewMeaning('')
    setReviewMeaningLoading(true)
    try {
      const response = await fetch(`/api/english-practice/meaning?word=${encodeURIComponent(word)}`)
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || '中文释义暂时无法获取')
      setReviewMeaning(result.meaning || '暂未补充释义')
    } catch (error) {
      setReviewMeaning('暂未补充释义')
      setNotice(error.message)
    } finally {
      setReviewMeaningLoading(false)
    }
  }

  async function prepareLibraryTestMeaning(word) {
    setLibraryTestMeaning('')
    setLibraryTestMeaningLoading(true)
    try {
      const response = await fetch(`/api/english-practice/meaning?word=${encodeURIComponent(word)}`)
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || '中文释义暂时无法获取')
      setLibraryTestMeaning(result.meaning || '暂未补充释义')
    } catch (error) {
      setLibraryTestMeaning('暂未补充释义')
      setNotice(error.message)
    } finally {
      setLibraryTestMeaningLoading(false)
    }
  }

  async function prepareLibraryTestExample(word, shouldPlay = true, accent = pronunciationAccent) {
    setLibraryTestExample(null)
    setLibraryTestExampleLoading(true)
    try {
      const response = await fetch(`/api/english-practice/dictation-example?word=${encodeURIComponent(word)}&accent=${accent}`)
      const example = await response.json()
      if (!response.ok) throw new Error(example.detail || '例句暂时无法生成')
      setLibraryTestExample(example)
      if (shouldPlay && example.audio_url) {
        window.__hunterWordAudio?.pause()
        const audio = new Audio(example.audio_url)
        window.__hunterWordAudio = audio
        audio.play().catch(() => {})
      }
    } catch (error) {
      setNotice(error.message)
    } finally {
      setLibraryTestExampleLoading(false)
    }
  }

  async function prepareLibraryTestChoices(word) {
    setLibraryTestChoices(null)
    setLibraryTestChoicesLoading(true)
    try {
      const response = await fetch('/api/ket-vocabulary/listening-options', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ word }) })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || '听力选项暂时无法生成')
      setLibraryTestChoices(result)
    } catch (error) {
      setNotice(error.message)
    } finally {
      setLibraryTestChoicesLoading(false)
    }
  }

  function replayLibraryTestPrompt(useAlternateAccent = false) {
    const current = libraryTestWords[libraryTestIndex]
    if (!current) return
    const accent = useAlternateAccent ? (pronunciationAccent === 'us' ? 'uk' : 'us') : pronunciationAccent
    if (libraryTestMode === 'word' || libraryTestMode === 'choice') {
      speakWord(current.word, null, accent)
      return
    }
    if (!useAlternateAccent && libraryTestExample?.audio_url) {
      window.__hunterWordAudio?.pause()
      const audio = new Audio(libraryTestExample.audio_url)
      window.__hunterWordAudio = audio
      audio.play().catch(() => {})
      return
    }
    prepareLibraryTestExample(current.word, true, accent)
  }

  function beginLibraryTest(items) {
    setLibraryTestWords(items)
    setLibraryTestIndex(0)
    setLibraryTestAnswer('')
    setLibraryTestResult(null)
    setLibraryTestExample(null)
    setLibraryTestChoices(null)
    setLibraryTestMistakeWord('')
    libraryTestStatsRef.current = { correct: 0, incorrect: 0 }
    setLibraryTestStats(libraryTestStatsRef.current)
    setLibraryTestSummary(null)
    setLibraryTestSession(true)
    if (items[0]) {
      prepareLibraryTestMeaning(items[0].word)
      if (libraryTestMode === 'word') speakWord(items[0].word)
      if (libraryTestMode === 'sentence') prepareLibraryTestExample(items[0].word)
      if (libraryTestMode === 'choice') {
        prepareLibraryTestChoices(items[0].word)
        speakWord(items[0].word)
      }
    }
  }

  async function startLibraryTest() {
    const count = Math.max(1, Math.min(100, Number(libraryTestCount) || 35))
    if (libraryTestScope === 'mistakes') {
      if (!selectedMistakeDates.length) return setNotice('请至少勾选一个错词日期。')
      const matchingWords = vocabulary.all.filter((word) => selectedMistakeDates.includes((word.created_at || '').slice(0, 10)))
      if (!matchingWords.length) return setNotice('所选日期暂时没有可测试的错词。')
      beginLibraryTest(shuffledWords(matchingWords, count))
      return
    }
    try {
      const response = await fetch('/api/ket-vocabulary/test', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ count }) })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || '单词测试暂时无法开始')
      beginLibraryTest(result.items || [])
    } catch (error) {
      setNotice(error.message)
    }
  }

  function checkLibraryTestAnswer(event) {
    event.preventDefault()
    const current = libraryTestWords[libraryTestIndex]
    if (!current || !libraryTestAnswer.trim()) return
    const result = libraryTestAnswer.trim().toLowerCase() === current.word.toLowerCase() ? 'correct' : 'incorrect'
    setLibraryTestResult(result)
    const nextStats = { ...libraryTestStatsRef.current, [result]: libraryTestStatsRef.current[result] + 1 }
    libraryTestStatsRef.current = nextStats
    setLibraryTestStats(nextStats)
    if (result === 'incorrect') recordLibraryTestMistake(current)
  }

  function checkLibraryTestChoice(choice) {
    const current = libraryTestWords[libraryTestIndex]
    if (!current || !libraryTestChoices || libraryTestResult) return
    const result = libraryTestChoices.none_of_above
      ? (choice === 'none' ? 'correct' : 'incorrect')
      : (choice === libraryTestChoices.answer ? 'correct' : 'incorrect')
    setLibraryTestResult(result)
    const nextStats = { ...libraryTestStatsRef.current, [result]: libraryTestStatsRef.current[result] + 1 }
    libraryTestStatsRef.current = nextStats
    setLibraryTestStats(nextStats)
    if (result === 'incorrect') recordLibraryTestMistake(current)
  }

  async function recordLibraryTestMistake(current) {
    if (!current) return
    try {
      const response = await fetch('/api/vocabulary', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ word: current.word, meaning: libraryTestMeaning, error_type: libraryTestMode === 'choice' ? '听力选词' : '拼写', source: libraryTestMode === 'choice' ? 'KET 听力选词' : 'KET 单词测试', ket_word_id: current.id }) })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || '加入错词本失败')
      setDashboard(result.dashboard)
      setLibraryTestMistakeWord(current.id)
    } catch (error) {
      setNotice(error.message)
    }
  }

  function advanceLibraryTest() {
    if (libraryTestIndex + 1 >= libraryTestWords.length) {
      setLibraryTestSession(false)
      setLibraryTestSummary({ ...libraryTestStatsRef.current, total: libraryTestWords.length, scope: libraryTestScope })
      setNotice('本轮 KET 单词测试完成了。')
      return
    }
    const next = libraryTestWords[libraryTestIndex + 1]
    setLibraryTestIndex((index) => index + 1)
    setLibraryTestAnswer('')
    setLibraryTestResult(null)
    setLibraryTestMistakeWord('')
    setLibraryTestChoices(null)
    prepareLibraryTestMeaning(next.word)
    if (libraryTestMode === 'word') speakWord(next.word)
    if (libraryTestMode === 'sentence') prepareLibraryTestExample(next.word)
    if (libraryTestMode === 'choice') {
      prepareLibraryTestChoices(next.word)
      speakWord(next.word)
    }
  }

  async function addKetWordToErrors() {
    if (!selectedKetWord) return
    try {
      const response = await fetch('/api/vocabulary', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ word: selectedKetWord.word, meaning: ketDetail?.translation || '', error_type: '词义', source: 'KET词库', ket_word_id: selectedKetWord.id }),
      })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || '错词挂接失败')
      setDashboard(result.dashboard)
      setNotice(`${result.message} 已关联 KET 词库。`)
    } catch (error) {
      setNotice(error.message)
    }
  }

  async function createMemoryPlan() {
    const words = memoryInput.split(/[\n,，、;；]+/).map((word) => word.trim()).filter(Boolean)
    if (!words.length) return setNotice('先输入至少两个想一起学习的单词。')
    try {
      const response = await fetch('/api/ket-vocabulary/memory-plan', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ words }) })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || '记忆计划生成失败')
      setMemoryPlan(result)
    } catch (error) {
      setNotice(error.message)
    }
  }

  function shuffledWords(words, count) {
    const unique = words.filter((word, index) => words.findIndex((item) => item.id === word.id) === index)
    for (let index = unique.length - 1; index > 0; index -= 1) {
      const randomIndex = Math.floor(Math.random() * (index + 1))
      ;[unique[index], unique[randomIndex]] = [unique[randomIndex], unique[index]]
    }
    return unique.slice(0, Math.min(count, unique.length))
  }

  function startInputReview(mode = 'meaning', count = 35) {
    const allCandidates = vocabulary.all.length ? vocabulary.all : vocabulary.today
    const candidates = reviewMistakeDates.length
      ? allCandidates.filter((word) => reviewMistakeDates.includes((word.created_at || '').slice(0, 10)))
      : allCandidates
    if (!candidates.length) return setNotice('先录入几条错词，才能开始随机测试。')
    const selectedWords = shuffledWords(candidates, count)
    setReviewSessionWords(selectedWords)
    setReviewIndex(0)
    setReviewAnswer('')
    setReviewResult(null)
    setReviewMode(mode)
    setDictationExample(null)
    setReviewMeaning('')
    setDictationPickerOpen(false)
    setReviewSession(true)
    if (mode === 'dictation') prepareDictationExample(selectedWords[0].word)
    prepareReviewMeaning(selectedWords[0].word, selectedWords[0].meaning)
  }

  function checkReviewAnswer(event) {
    event.preventDefault()
    const current = reviewSessionWords[reviewIndex]
    if (!current || !reviewAnswer.trim()) return
    setReviewResult(reviewAnswer.trim().toLowerCase() === current.word.toLowerCase() ? 'correct' : 'incorrect')
  }

  function advanceReview() {
    const current = reviewSessionWords[reviewIndex]
    if (current && reviewResult) reviewWord(current.id, reviewResult === 'correct' ? 'known' : 'unknown')
    if (reviewIndex + 1 >= reviewSessionWords.length) {
      setReviewSession(false)
      setNotice('这一轮输入复习完成了。')
      return
    }
    setReviewIndex((index) => index + 1)
    setReviewAnswer('')
    setReviewResult(null)
    if (reviewMode === 'dictation') prepareDictationExample(reviewSessionWords[reviewIndex + 1].word)
    prepareReviewMeaning(reviewSessionWords[reviewIndex + 1].word, reviewSessionWords[reviewIndex + 1].meaning)
  }

  const data = dashboard || {
    group: '六六班级', wechat_ready: false, qq_ready: false, qq_status: 'unavailable', qq_group: '2024级二（7）班（乐知班）', last_sync: null,
    automation: false, automation_time: '18:30', recent_messages: [], teacher_messages: [],
    teachers: [], teacher_stats: { total: 0, text: 0, attachment: 0 },
    voice_reminders_enabled: true, voice_reminders: [], homework_items: [],
    history: [], praise_records: [], praise_leaderboard: [], last_result: { captured: 0, saved: 0, duplicates: 0, duration: '—' },
    setup_hint: '正在连接本机服务…', screen_recording: false, vocabulary: { total: 0, due_count: 0, mastered_count: 0, today: [], difficult: [], all: [] },
  }
  const result = data.last_result
  const dailyRequirements = data.daily_requirements || []
  const selectedRequirementDate = requirementDate || dailyRequirements[0]?.date || ''
  const selectedDailyRequirements = dailyRequirements.find((day) => day.date === selectedRequirementDate)
  const teacherMessages = data.teacher_messages.filter((message) => (
    (messageType === '全部' || message.message_type === messageType)
    && (messageSource === '全部' || sourceLabel(message.source) === messageSource)
    && (teacherName === '全部' || message.sender === teacherName)
    && (!messageDate || message.message_date === messageDate)
  ))
  const homeworkItems = data.homework_items || []
  const vocabulary = data.vocabulary || { total: 0, due_count: 0, mastered_count: 0, today: [], difficult: [], all: [] }
  const mistakeDateOptions = [...new Set(vocabulary.all.map((word) => (word.created_at || '').slice(0, 10)).filter(Boolean))].sort().reverse()
  const selectedReviewWordCount = reviewMistakeDates.length ? vocabulary.all.filter((word) => reviewMistakeDates.includes((word.created_at || '').slice(0, 10))).length : vocabulary.all.length
  const alternateAccentLabel = pronunciationAccent === 'us' ? '英音' : '美音'
  const selectedHomework = homeworkItems.find((item) => item.id === selectedHomeworkId) || homeworkItems[0]
  const selectedReminder = selectedHomework && data.voice_reminders.find((reminder) => reminder.id === selectedHomework.id)

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><BookOpen size={28} /></span><span>六六学习记忆</span></div>
        <nav aria-label="主导航">
          {navigation.map(([label, Icon]) => (
            <button className={`nav-item ${activeView === label ? 'active' : ''}`} key={label} type="button" onClick={() => (label === '同步中心' || label === '老师要求' || label === '英语单词' || label === '作业提醒' || label === '老师画像' || label === '表扬档案') && setActiveView(label)}>
              <Icon size={19} strokeWidth={1.8} />{label}
            </button>
          ))}
        </nav>
        <div className="sidebar-status">
          <div><StatusDot online={data.wechat_ready} />{data.wechat_ready ? '微信已登录' : '微信等待连接'}</div>
          <p>监听群：{data.group}</p>
          <div className="sidebar-footer"><span>本地模式 1.0</span>{!data.screen_recording && <button className="permission-button" type="button" onClick={requestScreenRecording} title="打开屏幕录制设置" aria-label="打开屏幕录制设置"><MonitorUp size={15} /></button>}</div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div><h1>{activeView}</h1><p>{activeView === '老师要求' ? '按日期整理老师布置的作业、要求和资料。' : activeView === '作业提醒' ? '选择一条已识别作业，生成自然语音提醒。' : activeView === '老师画像' ? '从实际群消息提取老师的沟通风格与高频要求。' : activeView === '表扬档案' ? '记录每一次被老师明确表扬的成长瞬间。' : '将班群里的学习信息变成可复习的记忆。'}</p></div>
          <button className="icon-button" onClick={() => refresh().catch((error) => setNotice(error.message))} title="刷新状态"><RefreshCw size={19} /></button>
          <button className="icon-button" title="帮助"><HelpCircle size={19} /></button>
        </header>

        {notice && <div className="notice"><Sparkles size={17} /> <span>{notice}</span></div>}

        {activeView === '英语单词' ? reviewSession ? <section className="input-review-page panel">{reviewSessionWords[reviewIndex] ? <div className="input-review-card"><div className="review-progress"><button type="button" className="exit-review" onClick={() => { window.__hunterWordAudio?.pause(); setReviewSession(false) }}><XCircle size={16} />退出并返回错词复习</button><span>{reviewIndex + 1} / {reviewSessionWords.length}</span></div><span className="source-tag qq">{reviewMode === 'dictation' ? '听写默写' : '中文释义拼写'}</span>{reviewMode === 'dictation' ? <><h2>生活例句听写</h2><p className="prompt-label">目标词中文意思</p><h2 className="target-meaning">{reviewMeaningLoading ? '正在补全中文意思…' : reviewMeaning || '暂未补充释义'}</h2><p className="dictation-help">{dictationExampleLoading ? '正在准备例句…' : '听完例句后，写出与这个意思对应的英文单词。'}</p><button type="button" className="speak-word" onClick={() => replayDictationExample(true)} disabled={dictationExampleLoading}><Volume2 size={18} />我没听清，换成{alternateAccentLabel}再听</button></> : <><p className="prompt-label">中文意思</p><h2>{reviewMeaningLoading ? '正在补全中文意思…' : reviewMeaning || '暂未补充释义'}</h2></>}<p>{reviewSessionWords[reviewIndex].error_type} · {reviewSessionWords[reviewIndex].source}</p><form onSubmit={checkReviewAnswer}><input autoFocus disabled={Boolean(reviewResult)} value={reviewAnswer} onChange={(event) => setReviewAnswer(event.target.value)} placeholder="输入英文单词" autoComplete="off" /><button className="generate-voice" type="submit" disabled={!reviewAnswer || Boolean(reviewResult)}>检查拼写</button></form>{reviewResult && <div className={`review-feedback ${reviewResult}`}><strong>{reviewResult === 'correct' ? '答对了' : '再记一次'}</strong><span>正确拼写：{reviewSessionWords[reviewIndex].word}</span><span>单词意思：{reviewMeaning || '暂未补充释义'}</span>{reviewMode === 'dictation' && dictationExample ? <span className="example-reveal">例句：{dictationExample.sentence}<small>{dictationExample.translation}</small></span> : null}<button type="button" onClick={advanceReview}>{reviewIndex + 1 === reviewSessionWords.length ? '完成本轮复习' : '下一张'}</button></div>}</div> : null}</section> : <section className="vocabulary-view">
          <div className="english-tabs"><button type="button" className={englishView === '词库' ? 'selected' : ''} onClick={() => setEnglishView('词库')}>KET 词库</button><button type="button" className={englishView === '单词测试' ? 'selected' : ''} onClick={() => setEnglishView('单词测试')}>单词测试</button><button type="button" className={englishView === '错词复习' ? 'selected' : ''} onClick={() => setEnglishView('错词复习')}>错词复习</button><button type="button" className="start-input-review" onClick={() => startInputReview('meaning')}><RotateCcw size={15} />中文释义拼写</button><button type="button" className="start-input-review" onClick={() => setDictationPickerOpen((open) => !open)}><Volume2 size={15} />听写默写</button><div className="accent-toggle"><button type="button" className={pronunciationAccent === 'us' ? 'selected' : ''} onClick={() => setPronunciationAccent('us')}>美音</button><button type="button" className={pronunciationAccent === 'uk' ? 'selected' : ''} onClick={() => setPronunciationAccent('uk')}>KET 英音</button></div></div>
          {dictationPickerOpen ? <section className="dictation-picker panel"><div><strong>随机听写</strong><span>从我的错词表随机抽取，词序每次都会重新打乱。</span></div><div className="dictation-counts">{[10, 15, 20, 30, 35].map((count) => <button type="button" key={count} className={count === 35 ? 'default' : ''} onClick={() => startInputReview('dictation', count)}>{count === 35 ? '常规 35' : `${count} 个`}</button>)}</div></section> : null}
          <button type="button" className="choice-test-launch" onClick={() => { setEnglishView('单词测试'); setLibraryTestMode('choice') }}><Volume2 size={16} />听力选词测试</button>
          {englishView === '单词测试' && libraryTestMode === 'choice' ? <section className="listening-choice-test panel">{libraryTestSession && libraryTestWords[libraryTestIndex] ? <div className="library-test-card"><div className="review-progress"><button type="button" className="exit-review" onClick={() => { window.__hunterWordAudio?.pause(); setLibraryTestSession(false) }}><XCircle size={16} />退出并返回单词测试</button><span>{libraryTestIndex + 1} / {libraryTestWords.length}</span></div><span className="source-tag qq">{libraryTestScope === 'ket' ? 'KET / A2 Key 听力选词' : '日期错词听力选词'}</span><h2>听力选词</h2><p>{libraryTestChoicesLoading ? '正在准备 5 个选项…' : '听单词发音后，从四个词中选出听到的词；若四项都不是，选 E。'}</p><button type="button" className="speak-word" onClick={() => replayLibraryTestPrompt(true)} disabled={libraryTestChoicesLoading}><Volume2 size={18} />我没听清，换成{alternateAccentLabel}再听</button>{libraryTestChoices ? <div className="listening-choice-grid">{libraryTestChoices.choices.map((choice, index) => <button type="button" disabled={Boolean(libraryTestResult)} onClick={() => checkLibraryTestChoice(choice.word)} key={choice.id}>{String.fromCharCode(65 + index)}. {choice.word}</button>)}<button type="button" disabled={Boolean(libraryTestResult)} onClick={() => checkLibraryTestChoice('none')}>E. 以上都不是</button></div> : null}{libraryTestResult ? <div className={`review-feedback ${libraryTestResult}`}><strong>{libraryTestResult === 'correct' ? '答对了' : '这次没选对'}</strong><span>{libraryTestChoices?.none_of_above ? '正确选项：以上都不是' : `正确拼写：${libraryTestWords[libraryTestIndex].word}`}</span><span>单词意思：{libraryTestMeaning || '暂未补充释义'}</span>{libraryTestResult === 'incorrect' ? <span className="auto-mistake">{libraryTestMistakeWord === libraryTestWords[libraryTestIndex].id ? '已自动加入错词本（听力选词）' : '正在自动加入错词本…'}</span> : null}<button type="button" onClick={advanceLibraryTest}>{libraryTestIndex + 1 === libraryTestWords.length ? '完成本轮测试' : '下一题'}</button></div> : null}</div> : <div className="library-test-setup"><span className="source-tag qq">听力选词</span><h2>听力选词测试</h2><p>每题播放一个单词，A-D 是四个候选词，E 为“以上都不是”。错选会自动记入错词本。</p>{libraryTestSummary ? <div className="test-summary"><strong>上一轮测试</strong><span>{libraryTestSummary.total} 题 · 答对 {libraryTestSummary.correct} · 答错 {libraryTestSummary.incorrect}</span></div> : null}<div className="test-scope-picker"><span>题库范围</span><div><button type="button" className={libraryTestScope === 'ket' ? 'selected' : ''} onClick={() => setLibraryTestScope('ket')}>完整 KET 词库</button><button type="button" className={libraryTestScope === 'mistakes' ? 'selected' : ''} onClick={() => setLibraryTestScope('mistakes')}>按日期错词</button></div></div>{libraryTestScope === 'mistakes' ? <div className="mistake-date-picker"><span>勾选错词日期</span>{mistakeDateOptions.length ? mistakeDateOptions.map((date) => <label key={date}><input type="checkbox" checked={selectedMistakeDates.includes(date)} onChange={() => setSelectedMistakeDates((dates) => dates.includes(date) ? dates.filter((item) => item !== date) : [...dates, date])} />{date}<small>{vocabulary.all.filter((word) => (word.created_at || '').slice(0, 10) === date).length} 词</small></label>) : <p>还没有已录入的错词。</p>}</div> : null}<label>测试数量<input type="number" min="1" max="100" value={libraryTestCount} onChange={(event) => setLibraryTestCount(event.target.value)} /></label><span className="count-help">每轮可测试 1-100 个词，默认 35 个。</span><button type="button" className="generate-voice" onClick={startLibraryTest}>开始听力选词</button></div>}</section> : null}
          {englishView === '单词测试' ? <section className="library-test panel">{libraryTestSession && libraryTestWords[libraryTestIndex] ? <div className="library-test-card"><div className="review-progress"><button type="button" className="exit-review" onClick={() => { window.__hunterWordAudio?.pause(); setLibraryTestSession(false) }}><XCircle size={16} />退出并返回单词测试</button><span>{libraryTestIndex + 1} / {libraryTestWords.length}</span></div><span className="source-tag qq">{libraryTestScope === 'ket' ? 'KET / A2 Key 随机测试' : '日期错词测试'}</span>{libraryTestMode === 'meaning' ? <><p className="prompt-label">中文意思</p><h2>{libraryTestMeaningLoading ? '正在加载释义…' : libraryTestMeaning || '暂未补充释义'}</h2><p>请写出对应英文单词。</p></> : <><h2>{libraryTestMode === 'word' ? '听单词发音，默写英文' : '生活例句听写'}</h2>{libraryTestMode === 'sentence' ? <><p className="prompt-label">目标词中文意思</p><h2 className="target-meaning">{libraryTestMeaningLoading ? '正在加载释义…' : libraryTestMeaning || '暂未补充释义'}</h2></> : null}<p>{libraryTestExampleLoading ? '正在准备例句…' : libraryTestMode === 'sentence' ? '听完例句后，写出与这个意思对应的英文单词。' : '不显示单词，听完后写出英文拼写。'}</p><button type="button" className="speak-word" onClick={() => replayLibraryTestPrompt(true)} disabled={libraryTestExampleLoading}><Volume2 size={18} />我没听清，换成{alternateAccentLabel}再听</button></>}<form onSubmit={checkLibraryTestAnswer}><input autoFocus disabled={Boolean(libraryTestResult)} value={libraryTestAnswer} onChange={(event) => setLibraryTestAnswer(event.target.value)} placeholder="输入英文单词" autoComplete="off" /><button className="generate-voice" type="submit" disabled={!libraryTestAnswer || Boolean(libraryTestResult)}>检查答案</button></form>{libraryTestResult ? <div className={`review-feedback ${libraryTestResult}`}><strong>{libraryTestResult === 'correct' ? '答对了' : '这次没写对'}</strong><span>正确拼写：{libraryTestWords[libraryTestIndex].word}</span><span>单词意思：{libraryTestMeaning}</span>{libraryTestMode === 'sentence' && libraryTestExample ? <span className="example-reveal">例句：{libraryTestExample.sentence}<small>{libraryTestExample.translation}</small></span> : null}{libraryTestResult === 'incorrect' ? <span className="auto-mistake">{libraryTestMistakeWord === libraryTestWords[libraryTestIndex].id ? '已自动加入错词本' : '正在自动加入错词本…'}</span> : null}<button type="button" onClick={advanceLibraryTest}>{libraryTestIndex + 1 === libraryTestWords.length ? '完成本轮测试' : '下一题'}</button></div> : null}</div> : <div className="library-test-setup"><span className="source-tag wechat">{libraryTestScope === 'ket' ? '完整词库' : '日期错词'}</span><h2>单词测试</h2><p>{libraryTestScope === 'ket' ? `从 ${data.ket_library?.total || 1621} 个 KET / A2 Key 词条中随机抽题。` : '只从勾选日期录入的错词中随机抽题。'}</p>{libraryTestSummary ? <div className="test-summary"><strong>上一轮测试</strong><span>{libraryTestSummary.total} 题 · 答对 {libraryTestSummary.correct} · 答错 {libraryTestSummary.incorrect}</span></div> : null}<div className="test-scope-picker"><span>题库范围</span><div><button type="button" className={libraryTestScope === 'ket' ? 'selected' : ''} onClick={() => setLibraryTestScope('ket')}>完整 KET 词库</button><button type="button" className={libraryTestScope === 'mistakes' ? 'selected' : ''} onClick={() => setLibraryTestScope('mistakes')}>按日期错词</button></div></div>{libraryTestScope === 'mistakes' ? <div className="mistake-date-picker"><span>勾选错词日期</span>{mistakeDateOptions.length ? mistakeDateOptions.map((date) => <label key={date}><input type="checkbox" checked={selectedMistakeDates.includes(date)} onChange={() => setSelectedMistakeDates((dates) => dates.includes(date) ? dates.filter((item) => item !== date) : [...dates, date])} />{date}<small>{vocabulary.all.filter((word) => (word.created_at || '').slice(0, 10) === date).length} 词</small></label>) : <p>还没有已录入的错词。</p>}</div> : null}<div className="test-mode-picker"><span>测试方法</span><div><button type="button" className={libraryTestMode === 'meaning' ? 'selected' : ''} onClick={() => setLibraryTestMode('meaning')}>中文释义默写</button><button type="button" className={libraryTestMode === 'word' ? 'selected' : ''} onClick={() => setLibraryTestMode('word')}>单词发音听写</button><button type="button" className={libraryTestMode === 'sentence' ? 'selected' : ''} onClick={() => setLibraryTestMode('sentence')}>生活例句听写</button></div></div><label>测试数量<input type="number" min="1" max="100" value={libraryTestCount} onChange={(event) => setLibraryTestCount(event.target.value)} /></label><span className="count-help">每轮可测试 1-100 个词，默认 35 个。</span><button type="button" className="generate-voice" onClick={startLibraryTest}>开始随机测试</button></div>}</section> : englishView === '词库' ? <section className="ket-library">
            <div className="ket-library-head panel"><div><span className="source-tag wechat">官方范围</span><h2>KET / A2 Key 词库</h2><p>{data.ket_library?.total || 0} 个词条，按官方 A2 Key 词表建立；打开词条可听读音、查看释义与学习方法。</p></div><input value={ketQuery} onChange={(event) => setKetQuery(event.target.value)} placeholder="搜索单词或短语" /></div>
            <div className="ket-library-grid"><article className="ket-word-list panel"><div className="section-head"><h2><BookOpen size={19} />词条</h2><span className="sync-state">{ketWords.length} 项</span></div><div>{ketWords.map((word) => <button type="button" className={`ket-word-row ${selectedKetWord?.id === word.id ? 'selected' : ''}`} key={word.id} onClick={() => selectKetWord(word)}><strong>{word.word}</strong><span>{word.part_of_speech || '词条'}</span></button>)}</div></article>
              <article className="ket-detail panel">{selectedKetWord ? <div className="ket-detail-body"><span className="source-tag qq">A2 Key</span><h2>{selectedKetWord.word}</h2><p className="phonetic">{ketLoading ? '正在加载释义与读音…' : ketDetail?.phonetic || '点击朗读，跟读三遍'}</p><button type="button" className="speak-word" onClick={() => speakWord(selectedKetWord.word, ketDetail)}><Volume2 size={18} />朗读单词</button>{ketDetail?.audio && <audio controls preload="none" src={ketDetail.audio} />}<dl><div><dt>中文意思</dt><dd>{ketDetail?.translation || (ketLoading ? '正在加载…' : '暂未获取到释义，可点击词条重新加载')}</dd></div><div><dt>英文解释</dt><dd>{ketDetail?.definition || '暂无词典解释'}</dd></div><div><dt>词性</dt><dd>{selectedKetWord.part_of_speech || '—'}</dd></div></dl><div className="word-method"><h3>学习方法</h3><p>{ketDetail?.method || '先听读、再看图理解、遮住英文拼写，最后用它说一句生活句子。'}</p></div><button type="button" className="generate-voice" onClick={addKetWordToErrors}><Plus size={17} />标为我的错词</button></div> : <div className="empty"><Languages size={28} /><p>选择一个 KET 词条</p><span>读音、释义与学习方法会显示在这里。</span></div>}</article></div>
            <section className="memory-workshop panel"><div><h2><Sparkles size={19} />多词记忆工坊</h2><p>粘贴多个单词，用场景联想、主动回忆、交错拼写和间隔复习形成一轮训练。</p></div><textarea value={memoryInput} onChange={(event) => setMemoryInput(event.target.value)} placeholder="例如 accident, airport, ambulance, arrive" /><button type="button" className="generate-voice" onClick={createMemoryPlan}>生成记忆计划</button>{memoryPlan && <div className="memory-plan"><ol>{memoryPlan.steps.map((step) => <li key={step}>{step}</li>)}</ol>{memoryPlan.groups.map((group, index) => <div className="memory-group" key={index}><strong>第 {index + 1} 组</strong>{group.map((word) => <span key={word.id}>{word.word}{word.meaning ? ` · ${word.meaning}` : ''}</span>)}</div>)}{memoryPlan.unmatched.length ? <p className="unmatched">暂未在 KET 词库找到：{memoryPlan.unmatched.join('、')}</p> : null}</div>}</section>
          </section> : <>
          {englishView === '错词复习' ? <section className="review-date-filter panel"><div><strong>错词复习范围</strong><span>{reviewMistakeDates.length ? `已选 ${reviewMistakeDates.length} 个日期，共 ${selectedReviewWordCount} 个错词。` : `未筛选日期，将从全部 ${selectedReviewWordCount} 个错词中抽题。`}</span></div><div className="review-filter-controls"><details className="review-date-menu"><summary>选择错词日期{reviewMistakeDates.length ? `（${reviewMistakeDates.length}）` : ''}</summary><div className="review-date-menu-body"><div className="review-date-menu-actions"><button type="button" onClick={() => setReviewMistakeDates(mistakeDateOptions)}>全选日期</button><button type="button" onClick={() => setReviewMistakeDates([])}>清除筛选</button></div>{mistakeDateOptions.length ? mistakeDateOptions.map((date) => <label key={date}><input type="checkbox" checked={reviewMistakeDates.includes(date)} onChange={() => setReviewMistakeDates((dates) => dates.includes(date) ? dates.filter((item) => item !== date) : [...dates, date])} />{date}<small>{vocabulary.all.filter((word) => (word.created_at || '').slice(0, 10) === date).length} 词</small></label>) : <span>还没有已录入的错词。</span>}</div></details><div className="review-start-actions"><button type="button" onClick={() => startInputReview('meaning')}>开始中文拼写</button><select value={reviewDictationCount} onChange={(event) => setReviewDictationCount(Number(event.target.value))} aria-label="听写数量">{[10, 15, 20, 30, 35].map((count) => <option value={count} key={count}>{count === 35 ? '常规 35 词' : `${count} 词`}</option>)}</select><button type="button" onClick={() => startInputReview('dictation', reviewDictationCount)}>开始听写</button></div></div></section> : null}
          <section className="vocabulary-overview">
            <article className="vocab-stat panel"><span>错词总数</span><strong>{vocabulary.total}</strong><small>持续积累的英语知识点</small></article>
            <article className="vocab-stat panel due"><span>今日待复习</span><strong>{vocabulary.due_count}</strong><small>先处理最容易遗忘的词</small></article>
            <article className="vocab-stat panel mastered"><span>已稳定掌握</span><strong>{vocabulary.mastered_count}</strong><small>完成至少 4 个复习间隔</small></article>
          </section>
          <section className="vocabulary-workspace">
            <article className="word-entry panel"><div className="section-head"><h2><Plus size={19} />录入英语错词</h2></div><form onSubmit={saveWord}>
              <label>英文单词<input required value={wordForm.word} onChange={(event) => setWordForm({ ...wordForm, word: event.target.value })} placeholder="例如 because" />{wordLibraryChecking ? <span className="word-library-status checking">正在查询 KET 词库…</span> : wordLibraryMatch ? <span className="word-library-status linked"><Check size={14} />已在 KET / A2 Key 词库 · {wordLibraryMatch.part_of_speech || '词条'}，保存后自动挂接</span> : wordForm.word.trim().length >= 2 ? <span className="word-library-status unlinked">当前 KET / A2 Key 词库未找到，将作为自定义错词保存</span> : null}</label>
              <label>中文释义<input value={wordForm.meaning} onChange={(event) => setWordForm({ ...wordForm, meaning: event.target.value })} placeholder="例如 因为" /></label>
              <div className="word-form-row"><label>错误类型<select value={wordForm.error_type} onChange={(event) => setWordForm({ ...wordForm, error_type: event.target.value })}>{['拼写', '词义', '发音', '词形', '搭配'].map((item) => <option key={item}>{item}</option>)}</select></label><label>来源<select value={wordForm.source} onChange={(event) => setWordForm({ ...wordForm, source: event.target.value })}>{['听写', '作业', '试卷', '课堂', '自主发现'].map((item) => <option key={item}>{item}</option>)}</select></label></div>
              <label>备注<input value={wordForm.note} onChange={(event) => setWordForm({ ...wordForm, note: event.target.value })} placeholder="可选：错误句子或容易混淆的词" /></label>
              <button className="generate-voice" disabled={savingWord} type="submit">{savingWord ? <LoaderCircle className="spinning" size={17} /> : <Plus size={17} />}{savingWord ? '正在保存' : '加入错词本'}</button>
            </form></article>
            <article className="today-review panel"><div className="section-head"><h2><RotateCcw size={19} />今日复习</h2><span className="sync-state">{vocabulary.today.length} 词</span></div>
              {vocabulary.today.length ? <div className="review-list">{vocabulary.today.map((item) => <article key={item.id} className="review-card"><div><strong>{item.word}</strong><span>{item.meaning || '待补充释义'}</span><small>{item.error_type} · {item.source} · 错 {item.mistake_count} 次 · <b className={item.ket_word_id ? 'linked-ket' : 'unlinked-word'}>{item.ket_word_id ? '已挂接 KET 词库' : '未挂接词库'}</b></small></div><div className="review-actions"><button type="button" onClick={() => reviewWord(item.id, 'unknown')}>不会</button><button type="button" onClick={() => reviewWord(item.id, 'fuzzy')}>模糊</button><button type="button" className="repeat-review" onClick={() => reviewWord(item.id, 'repeat')}>今天再复习</button><button type="button" onClick={() => reviewWord(item.id, 'known')}>认识</button><button type="button" className={`delete-word ${pendingDeleteId === item.id ? 'confirm' : ''}`} title="删除错词" onClick={() => requestDelete(item)}>{pendingDeleteId === item.id ? '确认删除' : <Trash2 size={15} />}</button></div></article>)}</div> : <div className="empty"><Check size={26} /><p>今天的单词复习完成了</p><span>录入新的错词后会出现在这里。</span></div>}</article>
          </section>
          <section className="vocabulary-bottom">
            <article className="mini-quiz panel"><div className="section-head"><h2><ClipboardList size={19} />针对性小测</h2></div>{quizWords.length && quizIndex < quizWords.length ? <div className="quiz-card"><span>第 {quizIndex + 1} / {quizWords.length} 词</span><strong>{quizWords[quizIndex].word}</strong><p>先说出词义或拼写，再选择结果。</p><div className="review-actions"><button type="button" onClick={() => reviewWord(quizWords[quizIndex].id, 'unknown')}>不会</button><button type="button" onClick={() => reviewWord(quizWords[quizIndex].id, 'known')}>答对</button></div></div> : <div className="quiz-start"><p>{quizWords.length ? '本轮小测完成。' : '从今日待复习和高频错词中抽题。'}</p><button type="button" onClick={() => startQuiz(5)}>5 词小测</button><button type="button" onClick={() => startQuiz(10)}>10 词小测</button></div>}</article>
            <article className="difficult-words panel"><div className="section-head"><h2><Sparkles size={19} />高频错词</h2></div>{vocabulary.difficult.length ? <div className="difficult-list">{vocabulary.difficult.map((item) => <div key={item.id}><strong>{item.word}</strong><span>{item.meaning || '待补充释义'}</span><small>错误 {item.mistake_count} 次 · {item.ket_word_id ? 'KET 词库已挂接' : '未挂接词库'} · 下次 {item.next_review}</small></div>)}</div> : <div className="empty"><Languages size={26} /><p>从第一条错词开始</p></div>}</article>
          </section>
          </>}
        </section> : activeView === '作业提醒' ? <section className="homework-view">
          <div className="homework-list-panel panel"><div className="section-head"><h2><ClipboardList size={20} />已识别作业</h2><span className="sync-state">{homeworkItems.length} 条</span></div>
            {homeworkItems.length ? <div className="homework-list">{homeworkItems.map((item) => <button type="button" className={`homework-card ${selectedHomework?.id === item.id ? 'selected' : ''}`} onClick={() => setSelectedHomeworkId(item.id)} key={item.id}><span>{item.message_date}</span><strong>{item.teacher_subject || '综合'} · {item.sender} <em className={`source-tag ${item.source === 'qq_group' ? 'qq' : 'wechat'}`}>{sourceLabel(item.source)}</em></strong><p>{item.content}</p></button>)}</div> : <div className="empty"><ClipboardList size={26} /><p>暂无已识别作业</p><span>同步老师消息后会自动归入这里。</span></div>}
          </div>
          <aside className="voice-workbench panel">{selectedHomework ? <><div className="section-head"><h2><Volume2 size={20} />语音提醒</h2></div><div className="voice-workbench-body"><div className="message-tags"><span className="category homework">{selectedHomework.teacher_subject || '综合'}作业</span><span className={`source-tag ${selectedHomework.source === 'qq_group' ? 'qq' : 'wechat'}`}>{sourceLabel(selectedHomework.source)}</span></div><h2>{selectedHomework.sender}</h2><p>{selectedHomework.content}</p><div className="spoken-copy">六六，今天的{selectedHomework.teacher_subject || '学习'}作业，{selectedHomework.sender}老师是这样要求的：{selectedHomework.content}。记得认真完成，做完自己检查一遍。</div><button className="generate-voice" type="button" onClick={() => generateVoiceReminder(selectedHomework.id)} disabled={generatingVoice}>{generatingVoice ? <LoaderCircle className="spinning" size={18} /> : <Volume2 size={18} />}{selectedReminder ? '重新生成并播放' : '生成语音提醒'}</button>{selectedReminder && <audio controls key={selectedReminder.created_at} src={`/voice-reminders/${encodeURIComponent(selectedReminder.file)}`} />}</div></> : <div className="empty"><Volume2 size={26} /><p>选择一条作业</p></div>}</aside>
        </section> : activeView === '老师画像' ? <section className="knowledge-view">
          <div className="knowledge-intro panel"><div><h2><Sparkles size={20} />老师语言知识图谱</h2><p>节点来自已同步的真实群消息；主题的次数表示该老师在消息中提及该要求的频率。</p></div><span className="sync-state"><Check size={14} />本地分析</span></div>
          <div className="teacher-graph">
            {(data.teacher_knowledge_graph?.profiles || []).map((profile) => <article className="teacher-profile panel" key={profile.teacher}>
              <header><div className="teacher-node"><UserRound size={20} /><div><strong>{profile.teacher}</strong><span>{profile.subject} · {profile.message_count} 条消息 · {Object.entries(profile.sources || {}).map(([source, count]) => `${source} ${count} 条`).join(' · ')}</span></div></div><div className="style-tags">{profile.styles.map((style) => <span key={style}>{style}</span>)}</div></header>
              <div className="graph-links"><div className="graph-root">{profile.teacher}</div><div className="graph-topics">{profile.topics.length ? profile.topics.map((topic) => <div className="topic-node" key={topic.name}><span>{topic.name}</span><b>{topic.count}</b></div>) : <span className="no-topics">等待更多教学消息</span>}</div></div>
              <dl className="profile-metrics"><div><dt>老师要求</dt><dd>{profile.requirements}</dd></div><div><dt>作业消息</dt><dd>{profile.homework}</dd></div><div><dt>资料附件</dt><dd>{profile.attachments}</dd></div></dl>
              {profile.examples.length ? <div className="language-evidence"><h3>语言例证</h3>{profile.examples.map((example, index) => <p key={`${example.date}-${index}`}><time>{example.date}</time>{example.content}</p>)}</div> : null}
            </article>)}
          </div>
        </section> : activeView === '表扬档案' ? <section className="praise-view">
          <div className="praise-board panel"><div className="section-head"><h2><Trophy size={20} />表扬排行榜</h2><span className="sync-state"><Check size={14} />已识别</span></div>
            {data.praise_leaderboard.length ? <div className="praise-table"><table><thead><tr><th>小朋友</th><th>表扬次数</th><th>科目/维度</th></tr></thead><tbody>{data.praise_leaderboard.map((entry) => <tr key={entry.student}><td>{entry.student}</td><td><strong>{entry.count}</strong></td><td>{Object.entries(entry.subjects).map(([subject, count]) => `${subject} ${count} 次`).join(' · ')}</td></tr>)}</tbody></table></div> : <div className="empty"><Trophy size={26} /><p>暂无可确认姓名的表扬</p></div>}
          </div>
          <div className="praise-records panel"><div className="section-head"><h2><Bell size={20} />表扬记录</h2></div>
            {data.praise_records.length ? <div className="praise-list">{data.praise_records.map((record) => <article key={`${record.id}-${record.student}`}><div><strong>{record.student}</strong><span>{record.subject}</span><span className={`source-tag ${record.source === 'qq_group' ? 'qq' : 'wechat'}`}>{sourceLabel(record.source)}</span><time>{record.date}</time></div><p>{record.content}</p></article>)}</div> : <div className="empty"><Bell size={26} /><p>等待老师表扬记录</p></div>}
          </div>
        </section> : activeView === '老师要求' ? <section className="requirements-view panel">
          <div className="requirements-toolbar"><div><h2><CalendarDays size={20} />每日作业与要求</h2><p>按授课老师与学科整理作业、要求、考试提醒与资料附件。</p></div>
            <label>日期<select value={selectedRequirementDate} onChange={(event) => setRequirementDate(event.target.value)}>{dailyRequirements.map((day) => <option value={day.date} key={day.date}>{day.date}</option>)}</select></label>
          </div>
          {selectedDailyRequirements ? <div className="daily-requirements">
            <div className="daily-summary"><span>{selectedDailyRequirements.homework_count} 项作业</span><span>{selectedDailyRequirements.requirement_count} 条要求</span><span>{selectedDailyRequirements.attachment_count} 个附件</span></div>
            {selectedDailyRequirements.items.map((item) => <article className="requirement-item" key={item.id}><div className="requirement-tags"><span className={`category ${categoryClass[item.category] || 'ordinary'}`}>{item.message_type === '附件' ? '资料附件' : item.category}</span><span className={`source-tag ${item.source === 'qq_group' ? 'qq' : 'wechat'}`}>{sourceLabel(item.source)}</span></div><p>{item.content}</p><small>{item.sender} · {item.teacher_subject || '综合'}<br />{item.source_time || item.message_date}</small></article>)}
          </div> : <div className="empty"><ClipboardList size={26} /><p>暂无老师要求</p><span>同步后会按消息日期自动归档。</span></div>}
        </section> : <>
        <section className="overview-grid">
          <div className="sync-panel panel">
            <button className="sync-button" type="button" onClick={startSync} disabled={syncing}>
              {syncing ? <LoaderCircle className="spinning" size={24} /> : <RefreshCw size={24} />}
              {syncing ? '正在同步…' : `同步${data.group}`}
            </button>
            <button className="sync-button secondary-sync" type="button" onClick={startQqSync} disabled={qqSyncing || qqLoginStarting}>
              {qqSyncing ? <LoaderCircle className="spinning" size={20} /> : <MessageCircleMore size={20} />}
              {qqSyncing ? '正在同步 QQ…' : data.qq_ready ? `同步 QQ · ${data.qq_group}` : '登录 QQ 后同步'}
            </button>
            {qqLoginVisible && !data.qq_ready ? <div className="qq-login-panel"><div><strong>QQ 同步登录</strong><p>仅用于读取 QQ 班级群记录，不影响微信同步和其他学习功能。</p></div><img src={`/api/qq/login-qr?t=${qqLoginNonce}`} alt="QQ 登录二维码" /><div className="qq-login-actions"><button type="button" onClick={checkQqLogin}>检查 QQ 登录</button><button type="button" onClick={startQqLogin} disabled={qqLoginStarting}>{qqLoginStarting ? '正在生成…' : '刷新二维码'}</button></div></div> : null}
            <div className="connection-line">
              <span><StatusDot online={data.wechat_ready} />{data.wechat_ready ? '微信已登录' : '等待微信登录与授权'}</span>
              <i />
              <span><StatusDot online={data.qq_ready} />{data.qq_ready ? 'QQ 已登录' : data.qq_status === 'offline' ? 'QQ 登录已失效' : 'QQ 等待连接'}</span>
              <i />
              <span>最后同步：{formatTime(data.last_sync)}</span>
            </div>
            {!data.wechat_ready && <div className="setup-hint"><p>{data.setup_hint}</p></div>}
          </div>

          <section className="result-panel panel" aria-label="本次同步结果">
            <h2><FileText size={20} />本次同步结果</h2>
            <dl className="metrics">
              <div><dt><MessageCircleMore size={17} />新捕获消息</dt><dd>{result.captured}</dd></div>
              <div><dt><Check size={17} />已保存记录</dt><dd className="success">{result.saved}</dd></div>
              <div><dt><XCircle size={17} />跳过重复</dt><dd>{result.duplicates}</dd></div>
              <div><dt><Clock3 size={17} />处理耗时</dt><dd className="time">{result.duration}</dd></div>
            </dl>
            <div className="automation">
              <div><strong>自动化设置</strong><p>每日 {data.automation_time} 自动检查并归档新消息。</p></div>
              <label className="switch" aria-label="自动检查">
                <input type="checkbox" checked={data.automation} onChange={(event) => toggleAutomation(event.target.checked)} />
                <span />
              </label>
            </div>
            <div className="automation voice-reminder-setting">
              <div><strong>新作业语音提醒</strong><p>首次同步到新作业时，使用本机普通话语音播报，并保留回放。</p></div>
              <label className="switch" aria-label="新作业语音提醒">
                <input type="checkbox" checked={data.voice_reminders_enabled} onChange={(event) => toggleVoiceReminders(event.target.checked)} />
                <span />
              </label>
            </div>
          </section>
        </section>

        <section className="activity-panel panel">
          <div className="section-head teacher-head"><div><h2><UserRound size={20} />授课老师消息</h2><p>已同步 {data.teacher_stats.total} 条，文字 {data.teacher_stats.text} 条，附件 {data.teacher_stats.attachment} 条。</p></div><span className="sync-state"><Check size={14} />已同步</span></div>
          <div className="message-filters" aria-label="授课老师消息筛选">
            <label>老师<select value={teacherName} onChange={(event) => setTeacherName(event.target.value)}><option value="全部">全部老师</option>{data.teachers.map((teacher) => <option value={teacher.name} key={teacher.name}>{teacher.name}（{teacher.subject}）</option>)}</select></label>
            <div className="segmented" aria-label="来源筛选">{['全部', '微信', 'QQ'].map((source) => <button type="button" className={messageSource === source ? 'selected' : ''} onClick={() => setMessageSource(source)} key={source}>{source}</button>)}</div>
            <div className="segmented" aria-label="消息类型">{['全部', '文字', '附件'].map((type) => <button type="button" className={messageType === type ? 'selected' : ''} onClick={() => setMessageType(type)} key={type}>{type === '附件' && <Paperclip size={14} />}{type}</button>)}</div>
            <label>日期<input type="date" value={messageDate} onChange={(event) => setMessageDate(event.target.value)} /></label>
            {messageDate && <button className="clear-filter" type="button" onClick={() => setMessageDate('')}>清除日期</button>}
          </div>
          {teacherMessages.length ? <div className="timeline">
            {teacherMessages.map((message) => <article className="message teacher-message" key={message.id}>
              <time>{message.message_date || formatTime(message.captured_at)}</time><span className="timeline-dot" />
              <div><p>{message.content}</p><small>{message.sender} · {message.teacher_subject || '综合'} · {message.message_type} · {message.sync_status}</small></div><div className="message-tags"><span className={`source-tag ${message.source === 'qq_group' ? 'qq' : 'wechat'}`}>{sourceLabel(message.source)}</span><span className={`category ${categoryClass[message.category] || 'ordinary'}`}>{message.category}</span></div>
            </article>)}
          </div> : <div className="empty"><MessageCircleMore size={26} /><p>暂无符合条件的老师消息</p><span>同步后会自动按文字、附件和日期整理。</span></div>}
        </section>

        <section className="history-panel panel">
          <div className="section-head"><h2><ClipboardList size={20} />近期同步记录</h2></div>
          <div className="table-wrap"><table>
            <thead><tr><th>同步时间</th><th>群聊</th><th>新捕获</th><th>已保存</th><th>跳过重复</th><th>状态</th><th>耗时</th></tr></thead>
            <tbody>{data.history.length ? data.history.map((item) => <tr key={item.id}><td>{formatTime(item.finished_at)}</td><td>{data.group}</td><td>{item.captured}</td><td>{item.saved}</td><td>{item.duplicates}</td><td><span className={`run-status ${item.status}`}>{item.status === 'success' ? '成功' : '未完成'}</span></td><td>{item.duration}</td></tr>) : <tr><td colSpan="7" className="empty-row">尚无同步记录</td></tr>}</tbody>
          </table></div>
        </section>
        {data.voice_reminders.length ? <section className="voice-history panel"><div className="section-head"><h2><Bell size={20} />作业语音提醒</h2></div><div className="voice-list">{data.voice_reminders.slice(0, 6).map((reminder) => <article key={reminder.id}><div><p>{reminder.text}</p><time>{formatTime(reminder.created_at)}</time></div><audio controls preload="none" src={`/voice-reminders/${encodeURIComponent(reminder.file)}`} /></article>)}</div></section> : null}
        </>}
      </main>
    </div>
  )
}

export default App
