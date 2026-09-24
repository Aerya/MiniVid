/* MiniVid UI language switcher. French is the original/default language. */
(() => {
  const en = {
    "Stockage": "Storage", "← Retour": "← Back", "Ouvrir la page Stockage": "Open Storage",
    "Trier, examiner et protéger vos vidéos avant de libérer de la place.": "Sort, review and protect videos before freeing space.",
    "Analyser les doublons": "Scan for duplicates", "Copies vérifiées": "Verified copies", "Liens vers un même fichier physique": "Links to the same physical file",
    "Afficher": "Show", "Tous": "All", "Jamais lancés": "Never started", "Arrêtés avant 30 %": "Stopped before 30%", "Candidats": "Candidates", "Protégés": "Protected",
    "Taille décroissante": "Largest first", "Plus anciens fichiers": "Oldest file dates", "Détectés le plus tôt": "First detected", "Dernier visionnage le plus ancien": "Oldest viewing date", "Nombre de démarrages": "Playback starts", "Progression maximale": "Highest reached position",
    "Vidéo": "Video", "Fichier du": "File dated", "Lectures": "Plays", "Max.": "Max.", "Dernière fois": "Last played", "Décision": "Decision",
    "Candidat au nettoyage": "Cleanup candidate", "Conserver sans règle": "Keep without a rule", "Protéger définitivement": "Protect", "Autoriser le nettoyage": "Allow cleanup",
    "Ratio minimum": "Minimum ratio", "Temps de seed minimum (jours)": "Minimum seeding time (days)", "Condition": "Condition", "Ratio ET durée": "Ratio AND time", "Ratio OU durée": "Ratio OR time",
    "Déclencher": "Trigger", "Lorsque le stockage manque de place": "When storage is low", "Dès que les conditions sont atteintes": "As soon as conditions are met",
    "Espace libre sous (%)": "Free space below (%)", "Nettoyer jusqu'à (%)": "Clean until free (%)", "Enregistrer la décision": "Save decision",
    "Supprimer les autres copies": "Delete other copies", "Aucune copie physique vérifiée.": "No verified physical copies.",
    "Aucun lien physique partagé dans les sources.": "No shared physical link within the sources.",
    "Lancez une analyse pour vérifier les copies.": "Run a scan to verify copies.", "Analyse à lancer.": "Scan required.",
    "MiniVid ne supprime automatiquement que les vidéos autorisées ici, une fois les conditions de chaque torrent atteintes.": "MiniVid only deletes videos explicitly authorized here after all torrent conditions are met.",
    "Les copies sont vérifiées par SHA‑256. Les liens physiques et torrents cross-seed ne comptent pas comme plusieurs fichiers. La place indiquée reste une estimation sur les volumes avec snapshots ou reflinks.": "Copies are verified with SHA-256. Hardlinks and cross-seed torrents are not counted as separate files. Reclaimable space is an estimate on volumes with snapshots or reflinks.",
    "Accueil MiniVid": "MiniVid home", "Rechercher une vidéo, un dossier...": "Search a video or folder...",
    "Tri": "Sort", "Récentes": "Newest", "Nom": "Name", "Taille": "Size", "Résolution ↓": "Resolution ↓", "Résolution ↑": "Resolution ↑",
    "Non lues": "Unwatched", "Jamais lues": "Never watched", "Lues": "Watched", "Affichage": "Display", "Toutes": "All", "Tout": "All",
    "Par page": "Per page", "Mélange": "Order", "Dossiers d'abord": "Folders first", "Vidéos d'abord": "Videos first",
    "Vignettes": "Thumbnails", "Compact": "Compact", "Confort": "Comfortable", "Large": "Large", "Grouper par période": "Group by period",
    "Groupes": "Groups", "Favoris": "Favorites", "Collections": "Collections", "Thème clair/sombre": "Light/dark theme",
    "Maintenance": "Maintenance", "Déconnexion": "Log out", "← Parent": "← Parent", "Global": "All sources",
    "Afficher ou masquer les tags": "Show or hide tags", "Tags populaires": "Popular tags", "Masquer": "Hide", "Aucun tag": "No tags",
    "Tags sélectionnés": "Selected tags", "← Précédent": "← Previous", "Suivant →": "Next →", "Haut de page": "Back to top",
    "Aperçu vidéo": "Video preview", "Aperçu dossier": "Folder preview", "Sans tag": "No tags", "Lue": "Watched", "Non lue": "Unwatched",
    "VIDÉO": "VIDEO", "DOSSIER": "FOLDER", "Dernière modif.": "Last modified", "Aucun élément.": "No items.",
    "Utilisateur": "Username", "Mot de passe": "Password", "Se souvenir de moi": "Remember me", "Connexion": "Log in", "Entrer": "Enter",
    "Authentification désactivée. Définissez": "Authentication is disabled. Set", "pour l'activer.": "to enable it.",
    "Retour à la liste": "Back to library", "Retour": "Back", "Ce fichier vidéo est incomplet ou endommagé.": "This video file is incomplete or damaged.",
    "MiniVid a arrêté la lecture avant qu'elle ne boucle indéfiniment. Vérifiez ou retéléchargez le fichier source.": "MiniVid stopped playback before it could loop indefinitely. Check or download the source file again.",
    "Télécharger le fichier": "Download file", "Ce navigateur ne peut pas lire directement ce fichier .": "This browser cannot play this .",
    "et le transcodage est désactivé.": " file directly and transcoding is disabled.",
    "Activez": "Enable", "pour autoriser le remux/transcodage à la volée, ou utilisez un navigateur Chromium.": "to allow live remuxing/transcoding, or use a Chromium browser.",
    "Zoom": "Zoom", "Résolution :": "Resolution:", "+ Tag": "+ Tag", "Favori": "Favorite", "Marquer non lue": "Mark unwatched",
    "Marquer lue": "Mark watched", "Fichier et partage": "File and sharing", "Supprimer la vidéo": "Delete video", "Vidéos similaires": "Similar videos",
    "Raccourcis": "Shortcuts", "Lecture/Pause": "Play/Pause", "Reculer 10s": "Back 10s", "Avancer 10s": "Forward 10s", "Volume": "Volume",
    "Plein écran": "Fullscreen", "Muet": "Mute", "Indexation, cache et options partagées.": "Indexing, cache and shared options.",
    "Actions": "Actions", "Rescan complet": "Full rescan", "Purger miniatures": "Clear thumbnails", "Prêt.": "Ready.",
    "Journal récent": "Recent log", "Page précédente": "Previous page", "Précédent": "Previous", "Page suivante": "Next page", "Suivant": "Next", "Chargement...": "Loading...",
    "Affiche sous chaque vidéo une grille de contenus ayant des tags en commun. Ce réglage est stocké côté serveur.": "Shows a grid of videos sharing tags below each video. This setting is stored on the server.",
    "Activer": "Enable", "Enregistrer": "Save", "Sources vidéo et clients BitTorrent": "Video sources and BitTorrent clients",
    "Associez un client à une ou plusieurs sources pour afficher les statistiques du torrent. La suppression reste contrôlée par une option globale et un mode propre à chaque source.": "Associate a client with one or more sources to show torrent statistics. Deletion remains controlled by a global option and a setting for each source.",
    "Activer la liaison BitTorrent": "Enable BitTorrent integration", "Autoriser la suppression": "Allow deletion", "Clients": "Clients", "Ajouter un client": "Add client",
    "Association des sources": "Source association", "Enregistrer la configuration": "Save configuration", "Nom": "Name", "Type": "Type", "URL": "URL",
    "Liens du projet": "Project links", "MiniVid sur GitHub": "MiniVid on GitHub", "PornScout sur GitHub": "PornScout on GitHub",
    "Tester": "Test", "Retirer": "Remove", "Aucun client": "No client", "Chemin vu par le client": "Path seen by the client", "Suppression": "Deletion",
    "Désactivée": "Disabled", "Fichier uniquement": "File only", "Torrent et données": "Torrent and data", "Conservé si vide": "Kept if empty",
    "Démarrage du scan...": "Starting scan...", "Journal en direct...": "Live log...", "Mise à jour du journal...": "Updating log...", "Aucun événement": "No events",
    "Aucun journal": "No log", "Activé": "Enabled", "Désactivé": "Disabled", "Configuration enregistrée.": "Configuration saved.",
    "Test en cours...": "Test in progress...", "Connexion réussie": "Connection successful", "Enregistrement...": "Saving...", "Liaison active": "Integration enabled", "Liaison inactive": "Integration disabled",
    "Date": "Date", "Action": "Action", "Fichiers": "Files", "Modifiés": "Changed", "Durée": "Duration",
    "Ajouter des tags séparés par des virgules :": "Add comma-separated tags:", "Erreur tag": "Tag error", "Erreur favori": "Favorite error",
    "Erreur état de lecture": "Playback-state error", "Ouvrir": "Open", "le client BitTorrent": "the BitTorrent client",
    "Client BitTorrent :": "BitTorrent client:", "Gestion indisponible :": "Management unavailable:", "Confirmez la suppression": "Confirm deletion",
    "Supprimer la vidéo": "Delete video", "Suppression en cours...": "Deleting...", "Suppression refusée :": "Deletion refused:",
    "Cliquez une seconde fois pour effacer définitivement le fichier.": "Click a second time to permanently delete the file.",
    "Cliquez une seconde fois pour retirer": "Click a second time to remove", "torrent(s) et effacer leurs données.": "torrent(s) and delete their data.",
    "Attention : cette vidéo est dans vos favoris.": "Warning: this video is in your favorites.", "Supprimer le favori": "Delete favorite",
    "Démarrage...": "Starting...", "Scan complet en cours…": "Full scan in progress...", "Scan terminé": "Scan complete",
    "Erreur :": "Error:", "Erreur réseau :": "Network error:", "Erreur réseau purge :": "Thumbnail-clear network error:",
    "Miniatures supprimées :": "Thumbnails removed:", "Aucun journal": "No log", "Statut :": "Status:", "Scan en cours": "Scan in progress",
    "Configuration indisponible :": "Configuration unavailable:", "Configuration enregistrée. Enregistrez avant de tester un nouveau client.": "Configuration saved. Save before testing a new client."
  };

  const translateText = value => {
    const match = value.match(/^(\s*)(.*?)(\s*)$/s);
    const translated = en[match[2]];
    if (translated) return match[1] + translated + match[3];
    for (const [french, english] of Object.entries(en)) {
      if (match[2].startsWith(french + ' ')) return match[1] + english + match[2].slice(french.length) + match[3];
    }
    return value;
  };
  function translate(root = document.body) {
    const enabled = document.documentElement.lang === 'en';
    document.querySelectorAll('[data-i18n-original]').forEach(el => {
      if (!enabled) el.textContent = el.dataset.i18nOriginal;
    });
    if (!enabled) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => { const replacement = translateText(node.nodeValue); if (replacement !== node.nodeValue) node.nodeValue = replacement; });
    root.querySelectorAll?.('[title], [aria-label], [placeholder]').forEach(el => {
      ['title', 'aria-label', 'placeholder'].forEach(attr => {
        const value = el.getAttribute(attr); const replacement = value && en[value];
        if (replacement) el.setAttribute(attr, replacement);
      });
    });
  }

  async function setLanguage(lang) {
    document.documentElement.lang = lang;
    localStorage.setItem('minivid_lang', lang);
    document.querySelectorAll('.language-switcher button').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.lang === lang)));
    if (lang === 'en') translate(); else window.location.reload();
    try { await fetch('/api/preferences', { method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({lang}) }); } catch (_) {}
  }

  function mountSwitcher() {
    const host = document.querySelector('.header-right');
    if (!host || host.querySelector('.language-switcher')) return;
    const switcher = document.createElement('div');
    switcher.className = 'language-switcher';
    switcher.setAttribute('aria-label', 'Language / Langue');
    switcher.innerHTML = '<button type="button" data-lang="fr" title="Français" aria-label="Français">🇫🇷</button><button type="button" data-lang="en" title="English" aria-label="English">🇬🇧</button>';
    switcher.querySelectorAll('button').forEach(button => button.addEventListener('click', () => setLanguage(button.dataset.lang)));
    switcher.querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.lang === document.documentElement.lang)));
    host.prepend(switcher);
  }

  document.addEventListener('DOMContentLoaded', () => {
    const stored = localStorage.getItem('minivid_lang');
    if (stored === 'en' || stored === 'fr') document.documentElement.lang = stored;
    mountSwitcher(); translate();
    new MutationObserver(records => { if (document.documentElement.lang === 'en') records.forEach(record => record.addedNodes.forEach(node => {
      if (node.nodeType === Node.ELEMENT_NODE) translate(node);
      if (node.nodeType === Node.TEXT_NODE) node.nodeValue = translateText(node.nodeValue);
    })); }).observe(document.body, {childList: true, subtree: true});
  });
})();
