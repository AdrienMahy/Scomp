import { useEffect, useState } from 'react'
import { KeyRound, LockKeyhole, LogIn, ShieldCheck } from 'lucide-react'
import { completePasswordAction, loadPasswordActionInfo, login } from '../auth'

function AuthShell({ children, eyebrow = 'ACCÈS SÉCURISÉ', heroTitle, heroAccent, heroDescription }) {
  return <div className="auth-screen"><section className="auth-intro"><div className="auth-intro-top"><strong>SCOMP</strong><span>SPORTS DATA ETL</span></div><div className="auth-hero"><img src="/image/logo.png" alt="Scomp" /><span className="auth-divider" /><div><p className="eyebrow">{eyebrow}</p><h1>{heroTitle ? <>{heroTitle}<br /><em>{heroAccent}</em></> : <>Vos données sportives,<br /><em>prêtes à l’emploi.</em></>}</h1><p>{heroDescription || 'Collectez, transformez et fiabilisez les données de vos équipes dans un pipeline ETL unifié.'}</p></div></div><div className="auth-intro-badge"><ShieldCheck size={18} aria-hidden="true" /> Accès protégé par Scomp</div></section><section className="auth-panel"><div className="auth-panel-kicker">PLATEFORME ETL SPORTIVE</div>{children}</section></div>
}

export function LoginScreen({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const submit = async (event) => { event.preventDefault(); setError(''); setLoading(true); try { onLogin(await login(username, password)) } catch { setError('Identifiants invalides.'); } finally { setLoading(false) } }
  return <AuthShell><div className="auth-heading"><p className="eyebrow">CONNEXION</p><h2>Bienvenue dans Scomp</h2><p>Identifiez-vous pour accéder à vos pipelines TacticalData et STATSport.</p></div><form className="auth-form" onSubmit={submit}><label>Nom d’utilisateur<input value={username} onChange={event => setUsername(event.target.value)} autoComplete="username" required /></label><label>Mot de passe<input type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="current-password" required /></label>{error && <p className="auth-error" role="alert">{error}</p>}<button className="auth-submit" type="submit" disabled={loading}><LogIn size={18} aria-hidden="true" />{loading ? 'Connexion...' : 'Se connecter'}</button></form></AuthShell>
}

export function PasswordActionScreen({ mode, token, onComplete }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const isActivation = mode === 'activation'

  useEffect(() => {
    let active = true
    loadPasswordActionInfo(mode, token)
      .then(info => { if (active) setUsername(info.username) })
      .catch(() => { if (active) setError('Ce lien est invalide ou expiré.') })
    return () => { active = false }
  }, [mode, token])

  useEffect(() => {
    if (!message) return
    const timeout = window.setTimeout(onComplete, 1500)
    return () => window.clearTimeout(timeout)
  }, [message, onComplete])

  const submit = async event => {
    event.preventDefault()
    setError('')
    if (password.length < 12) return setError('Le mot de passe doit comporter au moins 12 caractères.')
    if (password !== confirmation) return setError('Les deux mots de passe doivent être identiques.')
    setLoading(true)
    try {
      await completePasswordAction(isActivation ? 'activate' : 'reset-password', token, password)
      setMessage(isActivation ? 'Votre compte est activé.' : 'Votre mot de passe a été modifié.')
    } catch {
      setError('Ce lien est invalide ou expiré.')
    } finally {
      setLoading(false)
    }
  }

  return <AuthShell eyebrow={isActivation ? 'ACTIVATION DU COMPTE' : 'MODIFICATION DU MOT DE PASSE'} heroTitle={isActivation ? 'Bienvenue chez' : 'Sécurisez votre'} heroAccent={isActivation ? 'Scomp.' : 'compte Scomp'} heroDescription={isActivation ? 'Votre accès aux données sportives est prêt. Définissez votre mot de passe pour commencer.' : 'Choisissez un nouveau mot de passe pour retrouver votre espace de travail.'}><div className="auth-heading"><KeyRound size={28} aria-hidden="true" /><h2>{isActivation ? 'Définir votre mot de passe' : 'Nouveau mot de passe'}</h2><p>{username ? <>{isActivation ? 'Bonjour' : 'Bonjour'}, <strong className="auth-user-name">{username}</strong>. {isActivation ? 'Choisissez un mot de passe pour activer votre compte.' : 'Vous pouvez choisir un nouveau mot de passe.'}</> : error || 'Vérification de votre lien sécurisé…'}</p></div>{message ? <div className="auth-success" role="status">{message}<p>Redirection automatique vers la connexion…</p></div> : <form className="auth-form" onSubmit={submit}><label>Nouveau mot de passe<input type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="new-password" required minLength={12} disabled={!username} /></label><label>Confirmer le mot de passe<input type="password" value={confirmation} onChange={event => setConfirmation(event.target.value)} autoComplete="new-password" required minLength={12} disabled={!username} /></label>{error && <p className="auth-error" role="alert">{error}</p>}<button className="auth-submit" type="submit" disabled={loading || !username}><LockKeyhole size={18} aria-hidden="true" />{loading ? 'Enregistrement…' : isActivation ? 'Activer mon compte' : 'Enregistrer le nouveau mot de passe'}</button></form>}</AuthShell>
}
