import { useEffect, useMemo, useState } from 'react'
import { Check, Copy, KeyRound, Plus, Search, Save, ShieldCheck } from 'lucide-react'
import axios from 'axios'

const emptyForm = () => ({ username: '', email: '', group_name: '', tactical_access: true, statsport_access: true })

function toForm(user) {
  return {
    username: user.username || '',
    email: user.email || '',
    group_name: user.group_name || '',
    tactical_access: Boolean(user.tactical_access),
    statsport_access: Boolean(user.statsport_access),
  }
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState([])
  const [selectedUserId, setSelectedUserId] = useState(null)
  const [isCreating, setIsCreating] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [search, setSearch] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [generatedLink, setGeneratedLink] = useState('')
  const [linkKind, setLinkKind] = useState('activation')
  const [copied, setCopied] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [linkLoading, setLinkLoading] = useState(false)

  const selectedUser = users.find(user => user.id === selectedUserId) || null
  const filteredUsers = useMemo(() => {
    const query = search.trim().toLocaleLowerCase('fr')
    if (!query) return users
    return users.filter(user => [user.username, user.email, user.group_name].some(value => value?.toLocaleLowerCase('fr').includes(query)))
  }, [users, search])

  const load = async () => {
    try {
      const response = await axios.get('/api/admin/users')
      setUsers(response.data)
      setSelectedUserId(current => current || response.data[0]?.id || null)
      if (response.data.length) setForm(current => current.username ? current : toForm(response.data[0]))
    } catch {
      setError('Impossible de charger les utilisateurs.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const selectUser = user => {
    setSelectedUserId(user.id)
    setIsCreating(false)
    setForm(toForm(user))
    setGeneratedLink('')
    setMessage('')
    setError('')
  }

  const startCreate = () => {
    setSelectedUserId(null)
    setIsCreating(true)
    setForm(emptyForm())
    setGeneratedLink('')
    setMessage('')
    setError('')
  }

  const updateForm = event => setForm(current => ({ ...current, [event.target.name]: event.target.type === 'checkbox' ? event.target.checked : event.target.value }))

  const save = async event => {
    event.preventDefault()
    setMessage('')
    setError('')
    setGeneratedLink('')
    setSaving(true)
    try {
      if (isCreating) {
        const response = await axios.post('/api/admin/users', form)
        const createdUser = response.data.user
        setUsers(current => [...current, createdUser])
        setSelectedUserId(createdUser.id)
        setIsCreating(false)
        setForm(toForm(createdUser))
        setGeneratedLink(response.data.activation_link)
        setLinkKind('activation')
        setMessage('Compte créé. Transmettez le lien d’activation à l’utilisateur.')
      } else if (selectedUser) {
        const response = await axios.patch(`/api/admin/users/${selectedUser.id}`, form)
        setUsers(current => current.map(user => user.id === response.data.id ? response.data : user))
        setForm(toForm(response.data))
        setMessage('Les informations du compte ont été enregistrées.')
      }
    } catch (reason) {
      setError(reason.response?.data?.detail || 'Impossible d’enregistrer le compte.')
    } finally {
      setSaving(false)
    }
  }

  const generateLink = async () => {
    if (!selectedUser) return
    setMessage('')
    setError('')
    setGeneratedLink('')
    setCopied(false)
    setLinkLoading(true)
    const kind = selectedUser.password_configured ? 'reset' : 'activation'
    const endpoint = kind === 'reset' ? 'reset-link' : 'activation-link'
    try {
      const response = await axios.post(`/api/admin/users/${selectedUser.id}/${endpoint}`)
      setGeneratedLink(kind === 'reset' ? response.data.reset_link : response.data.activation_link)
      setLinkKind(kind)
      setMessage(kind === 'reset' ? 'Lien de modification prêt à transmettre.' : 'Lien d’activation prêt à transmettre.')
    } catch {
      setError('Impossible de générer le lien sécurisé.')
    } finally {
      setLinkLoading(false)
    }
  }

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(generatedLink)
      setCopied(true)
    } catch {
      setError('La copie automatique est indisponible. Sélectionnez le lien pour le copier.')
    }
  }

  return (
    <section className="admin-users-page">
      <header className="admin-users-header">
        <div>
          <p className="eyebrow">SYSTÈME / ACCÈS</p>
          <h1>Gestion des utilisateurs</h1>
          <p>Comptes, accès aux projets et liens de sécurité.</p>
        </div>
        <div className="admin-users-total"><strong>{users.length}</strong><span>compte{users.length > 1 ? 's' : ''}</span></div>
      </header>

      {message && <p className="admin-users-feedback is-success" role="status">{message}</p>}
      {error && <p className="admin-users-feedback is-error" role="alert">{error}</p>}

      <div className="admin-user-workspace">
        <aside className="admin-user-directory" aria-label="Liste des utilisateurs">
          <div className="admin-directory-heading"><div><strong>Utilisateurs</strong><small>{users.length} compte{users.length > 1 ? 's' : ''}</small></div><button type="button" className="admin-new-user-button" onClick={startCreate}><Plus size={15} aria-hidden="true" /><span>Nouvel utilisateur</span></button></div>
          <label className="admin-user-search"><Search size={15} aria-hidden="true" /><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Rechercher…" aria-label="Rechercher un utilisateur" /></label>
          {loading ? <p className="admin-directory-state">Chargement des utilisateurs…</p> : filteredUsers.length === 0 ? <p className="admin-directory-state">{users.length ? 'Aucun utilisateur correspondant.' : 'Aucun utilisateur enregistré.'}</p> : <div className="admin-user-directory-list">
            {filteredUsers.map(user => <button type="button" className={`admin-directory-user ${selectedUserId === user.id && !isCreating ? 'is-selected' : ''}`} key={user.id} onClick={() => selectUser(user)}>
              <span className="admin-directory-avatar">{user.username.slice(0, 1).toUpperCase()}</span>
              <span className="admin-directory-identity"><strong>{user.username}</strong><small>{user.group_name || (user.is_admin ? 'Administrateur' : user.email || 'Sans groupe')}</small></span>
              <i className={`admin-directory-status ${user.password_configured ? 'is-ready' : ''}`} title={user.password_configured ? 'Mot de passe configuré' : 'Activation en attente'} />
            </button>)}
          </div>}
        </aside>

        <form className="admin-user-details" onSubmit={save}>
          <header className="admin-details-heading"><div><h2>{isCreating ? 'Nouvel utilisateur' : selectedUser?.username || 'Sélectionner un utilisateur'}</h2><p>{isCreating ? 'Renseignez les informations du compte et ses accès.' : 'Modifiez les informations et les droits du compte.'}</p></div>{!isCreating && selectedUser && <span className={`admin-account-status ${selectedUser.password_configured ? 'is-ready' : ''}`}><i />{selectedUser.password_configured ? 'Compte activé' : 'Activation en attente'}</span>}</header>

          <fieldset className="admin-details-section">
            <legend>Informations du compte</legend>
            <div className="admin-details-fields">
              <label>Nom d’utilisateur<input name="username" value={form.username} onChange={updateForm} autoComplete="off" required minLength="2" /></label>
              <label>Email<input name="email" type="email" value={form.email} onChange={updateForm} autoComplete="email" placeholder="nom@exemple.fr" required={isCreating} /></label>
              <label className="admin-group-field">Groupe <small>Facultatif · sans effet pour le moment</small><input name="group_name" value={form.group_name} onChange={updateForm} placeholder="Aucun groupe" /></label>
            </div>
          </fieldset>

          <fieldset className="admin-details-section">
            <legend>Accès aux projets</legend>
            {selectedUser?.is_admin && <p className="admin-full-access-note"><ShieldCheck size={14} aria-hidden="true" /> Les comptes administrateurs disposent d’un accès complet.</p>}
            <div className="admin-project-access-list">
              <label><input type="checkbox" name="tactical_access" checked={selectedUser?.is_admin || form.tactical_access} disabled={selectedUser?.is_admin} onChange={updateForm} /><span><strong>TacticalData</strong><small>Vue d’ensemble, matchs et données tactiques</small></span></label>
              <label><input type="checkbox" name="statsport_access" checked={selectedUser?.is_admin || form.statsport_access} disabled={selectedUser?.is_admin} onChange={updateForm} /><span><strong>STATSport</strong><small>Activités, joueurs et données physiques</small></span></label>
            </div>
          </fieldset>

          {!isCreating && selectedUser && <fieldset className="admin-details-section admin-security-section">
            <legend>Sécurité</legend>
            <div className="admin-security-action"><button type="button" className="admin-link-button" onClick={generateLink} disabled={linkLoading}><KeyRound size={15} aria-hidden="true" />{linkLoading ? 'Génération…' : selectedUser.password_configured ? 'Générer un lien de modification' : 'Générer un lien d’activation'}</button><small>Le lien permet de définir ou modifier le mot de passe.</small></div>
            {generatedLink && <div className="admin-generated-link"><label htmlFor="admin-generated-link">Lien {linkKind === 'activation' ? 'd’activation' : 'de modification'}</label><div><input id="admin-generated-link" readOnly value={generatedLink} onFocus={event => event.target.select()} /><button type="button" onClick={copyLink} aria-label="Copier le lien" title={copied ? 'Lien copié' : 'Copier le lien'}>{copied ? <Check size={15} aria-hidden="true" /> : <Copy size={15} aria-hidden="true" />}</button></div></div>}
          </fieldset>}

          {isCreating && <p className="admin-create-note"><KeyRound size={14} aria-hidden="true" /> Un lien d’activation sera généré après la création du compte.</p>}
          <footer className="admin-details-footer"><button className="admin-save-button" type="submit" disabled={saving || (!isCreating && !selectedUser)}><Save size={15} aria-hidden="true" />{saving ? 'Enregistrement…' : isCreating ? 'Créer le compte' : 'Enregistrer les modifications'}</button></footer>
        </form>
      </div>
    </section>
  )
}
