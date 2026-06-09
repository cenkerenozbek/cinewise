export interface AvatarDef {
  id: string;
  file: string;
  name: string;
  description: string;
}

export const AVATARS: AvatarDef[] = [
  {
    id: 'noir-detective',
    file: '/avatars/noir-detective.png',
    name: 'The Detective',
    description: 'A Film Noir classic. Sees clues others miss.',
  },
  {
    id: 'knight',
    file: '/avatars/knight.png',
    name: 'The Knight',
    description: 'Battle-worn and unbreakable. Epic cinema devotee.',
  },
  {
    id: 'jazz-musician',
    file: '/avatars/jazz-musician.png',
    name: 'The Musician',
    description: 'Soulful storyteller. Loves films with a beat.',
  },
  {
    id: 'cyberpunk-hacker',
    file: '/avatars/cyberpunk-hacker.png',
    name: 'The Hacker',
    description: 'Lives in the future. Sci-fi and dystopia obsessed.',
  },
  {
    id: 'victorian-inventor',
    file: '/avatars/victorian-inventor.png',
    name: 'The Inventor',
    description: 'Eccentric genius. Steampunk and period drama fan.',
  },
  {
    id: 'samurai',
    file: '/avatars/samurai.png',
    name: 'The Samurai',
    description: 'Disciplined and focused. World cinema connoisseur.',
  },
  {
    id: 'spy-agent',
    file: '/avatars/spy-agent.png',
    name: 'The Spy',
    description: 'Cool under pressure. Thriller and espionage lover.',
  },
  {
    id: 'romantic',
    file: '/avatars/romantic.png',
    name: 'The Romantic',
    description: 'Believes in great love stories. Drama at heart.',
  },
  {
    id: 'horror-survivor',
    file: '/avatars/horror-survivor.png',
    name: 'The Survivor',
    description: 'Faces the darkness. Horror and suspense specialist.',
  },
  {
    id: 'scifi-rebel',
    file: '/avatars/scifi-rebel.png',
    name: 'The Rebel',
    description: 'Fights the system. Dystopian sci-fi is home.',
  },
  {
    id: 'outlaw',
    file: '/avatars/outlaw.jpg',
    name: 'The Outlaw',
    description: 'Rides alone. Western and adventure film devotee.',
  },
  {
    id: 'space-explorer',
    file: '/avatars/space-explorer.png',
    name: 'The Explorer',
    description: 'Gazes at the stars. Space opera and wonder films.',
  },
];
