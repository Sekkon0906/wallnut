export interface Avatar {
  height: number
  build: string
  fur: string
  texture: string
  tail: string
  glasses: string
  headwear: string
  outfit: string
  accessory: string
}

export const defaultAvatar: Avatar = {
  height: 100, build: 'rounded', fur: 'amber', texture: 'smooth', tail: 'curled',
  glasses: 'none', headwear: 'none', outfit: 'hoodie', accessory: 'none',
}

export interface ArdyProfile {
  avatar: Avatar
  show_in_ranking: boolean
  career: string | null
}

export interface ArdyItem {
  id: string
  name: string
  price?: number
  rarity?: Rarity
  slot: 'outfit' | 'headwear'
  value: string
  owned: boolean
}

export type Rarity = 'normal' | 'special' | 'epic' | 'legendary'
export const rarityLabels: Record<Rarity, string> = {
  normal: 'Normal', special: 'Especial', epic: 'Épica', legendary: 'Legendaria',
}

export const careerLooks: { name: string; details: Partial<Avatar> }[] = [
  { name: 'Ingenierías', details: { headwear: 'helmet', outfit: 'jacket', fur: 'gray' } },
  { name: 'Diseño y Arquitectura', details: { glasses: 'round', headwear: 'cap', fur: 'cream', texture: 'wavy' } },
  { name: 'Economía y Administración', details: { outfit: 'jacket', glasses: 'square', fur: 'chestnut' } },
  { name: 'Derecho y Ciencias Sociales', details: { accessory: 'backpack', outfit: 'hoodie', tail: 'fluffy' } },
]

export interface RankingEntry {
  student_id: string
  display_name: string
  points: number
  activities: number
  position: number
  avatar: Avatar
  is_me: boolean
}

export const avatarControls = [
  { key: 'build', label: 'Complexión', options: [['slender', 'Delgada'], ['rounded', 'Redonda'], ['athletic', 'Atlética']] },
  { key: 'fur', label: 'Color de pelaje', options: [['amber', 'Ámbar'], ['chestnut', 'Castaño'], ['gray', 'Gris'], ['cream', 'Crema']] },
  { key: 'texture', label: 'Textura', options: [['smooth', 'Lisa'], ['wavy', 'Ondulada'], ['curly', 'Rizada']] },
  { key: 'tail', label: 'Cola', options: [['curled', 'En espiral'], ['fluffy', 'Voluminosa']] },
  { key: 'glasses', label: 'Gafas', options: [['none', 'Sin gafas'], ['round', 'Redondas'], ['square', 'Cuadradas']] },
  { key: 'headwear', label: 'Sombrero', options: [['none', 'Sin sombrero'], ['cap', 'Gorra'], ['helmet', 'Casco']] },
  { key: 'outfit', label: 'Ropa', options: [['none', 'Sin ropa'], ['hoodie', 'Buzo'], ['jacket', 'Chaqueta']] },
  { key: 'accessory', label: 'Accesorio', options: [['none', 'Sin accesorio'], ['chain', 'Cadena'], ['backpack', 'Mochila']] },
] as const

const palettes: Record<string, [string, string, string]> = {
  amber: ['#ce7436', '#a54d22', '#ffe0ae'],
  chestnut: ['#975642', '#6a342d', '#ffddbc'],
  gray: ['#8994a8', '#5c627c', '#f5e9e1'],
  cream: ['#e7bb87', '#b57754', '#fff2dd'],
}
const jacketColors: Record<string, [string, string]> = {
  purple_jacket: ['#7142a6', '#f0bd62'],
  reef_jacket: ['#136c75', '#ffa791'],
  nebula_jacket: ['#442468', '#ddacff'],
  solar_jacket: ['#51232d', '#ffca58'],
}
const capColors: Record<string, [string, string, string]> = {
  cap: ['#2457a8', '#3c7ed2', '#d7ecfd'],
  gold_cap: ['#a16314', '#e9ac39', '#fff0a7'],
  rust_cap: ['#9c4135', '#ce6b4a', '#faccac'],
  moon_cap: ['#372951', '#7773b7', '#e3d4fd'],
}

export function drawArdy(canvas: HTMLCanvasElement, avatar: Avatar) {
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const [fur, shade, cream] = palettes[avatar.fur] ?? palettes.amber!
  const ink = '#292643'

  function oval(x: number, y: number, rx: number, ry: number, fill: string, tilt = 0) {
    ctx!.beginPath()
    ctx!.ellipse(x, y, rx, ry, tilt, 0, Math.PI * 2)
    ctx!.fillStyle = fill
    ctx!.fill()
  }

  function line(color: string, width: number, trace: (context: CanvasRenderingContext2D) => void) {
    ctx!.beginPath()
    ctx!.lineWidth = width
    ctx!.strokeStyle = color
    ctx!.lineCap = 'round'
    ctx!.lineJoin = 'round'
    trace(ctx!)
    ctx!.stroke()
  }

  function patches(x: number, y: number, rows: number, cols: number, gap: number) {
    if (avatar.texture === 'smooth') return
    ctx!.save()
    ctx!.globalAlpha = 0.23
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const dx = x + c * gap + (r % 2) * 4
        const dy = y + r * gap
        line(shade, 1.8, p => {
          p.moveTo(dx - 3, dy)
          if (avatar.texture === 'curly') p.arc(dx, dy, 3, Math.PI, Math.PI * 2.35)
          else p.quadraticCurveTo(dx, dy - 5, dx + 5, dy)
        })
      }
    }
    ctx!.restore()
  }

  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.save()
  ctx.scale(canvas.width / 400, canvas.height / 360)
  oval(197, 322, 121, 14, '#172d5720')
  ctx.translate(177, 314)
  ctx.scale(1, avatar.height / 100)

  const fluffy = avatar.tail === 'fluffy'
  oval(fluffy ? 99 : 104, fluffy ? -156 : -135, fluffy ? 65 : 54, fluffy ? 108 : 86, shade, 0.48)
  oval(fluffy ? 103 : 108, fluffy ? -163 : -141, fluffy ? 57 : 47, fluffy ? 97 : 72, fur, 0.48)
  if (!fluffy) {
    line(cream, 6, p => {
      p.moveTo(91, -81)
      p.bezierCurveTo(161, -100, 172, -169, 133, -177)
      p.bezierCurveTo(105, -188, 89, -149, 110, -135)
      p.bezierCurveTo(123, -127, 136, -141, 128, -151)
    })
  } else {
    line(cream, 5, p => {
      p.moveTo(83, -76)
      p.quadraticCurveTo(104, -153, 148, -220)
    })
  }
  patches(114, -185, 2, 2, 15)

  const width = avatar.build === 'slender' ? 48 : avatar.build === 'athletic' ? 66 : 59
  if (avatar.accessory === 'backpack') {
    oval(-45, -84, 35, 53, '#2c4678')
    oval(-51, -77, 24, 34, '#557fb1')
  }
  oval(-29, -9, 29, 15, shade, -0.16)
  oval(31, -9, 29, 15, shade, 0.16)
  oval(0, -65, width, 57, fur)
  oval(0, -48, width * 0.61, 36, cream)
  oval(-width + 3, -66, 15, 37, shade, -0.4)
  oval(width - 3, -66, 15, 37, shade, 0.4)

  if (avatar.outfit !== 'none') {
    const hoodie = avatar.outfit === 'hoodie' || avatar.outfit === 'sage_hoodie'
    const sage = avatar.outfit === 'sage_hoodie'
    const [jacketColor, trim] = jacketColors[avatar.outfit] ?? ['#273d6c', '#f0bd62']
    oval(0, -66, width - 1, 50, hoodie ? (sage ? '#56755e' : '#3374c5') : jacketColor)
    if (hoodie) {
      oval(0, -89, width * 0.63, 25, sage ? '#375a4b' : '#174f9b')
      line('#c5e2ff', 3, p => { p.moveTo(-13, -88); p.lineTo(-16, -56); p.moveTo(13, -88); p.lineTo(16, -56) })
      line(sage ? '#b3d0b2' : '#9ec8fc', 3, p => { p.moveTo(-28, -40); p.quadraticCurveTo(0, -29, 28, -40) })
    } else {
      line('#d5e7ff', 4, p => { p.moveTo(0, -101); p.lineTo(0, -26) })
      oval(27, -65, 8, 8, trim)
      if (avatar.outfit === 'solar_jacket') {
        line(trim, 5, p => { p.moveTo(-44, -90); p.lineTo(-32, -55); p.moveTo(44, -90); p.lineTo(32, -55) })
        oval(30, -67, 5.5, 5.5, jacketColor)
      } else if (avatar.outfit === 'nebula_jacket') {
        oval(-26, -64, 3, 3, trim)
        oval(-36, -54, 2, 2, trim)
        oval(-16, -50, 2.5, 2.5, trim)
      }
    }
  }
  if (avatar.accessory === 'chain') {
    line('#e6ba50', 5, p => { p.moveTo(-28, -95); p.quadraticCurveTo(0, -56, 28, -95) })
    oval(0, -75, 5, 5, '#ffdf7b')
  }

  oval(-45, -205, 23, 32, shade, -0.29)
  oval(45, -205, 23, 32, shade, 0.29)
  oval(-45, -207, 14, 23, cream, -0.29)
  oval(45, -207, 14, 23, cream, 0.29)
  oval(0, -156, 66, 64, shade)
  oval(0, -162, 64, 61, fur)
  oval(-20, -125, 36, 25, cream, 0.13)
  oval(20, -125, 36, 25, cream, -0.13)
  patches(-23, -204, 2, 4, 13)
  oval(-22, -165, 15, 21, '#fffaf3')
  oval(22, -165, 15, 21, '#fffaf3')
  oval(-18, -164, 8.6, 13, ink)
  oval(19, -164, 8.6, 13, ink)
  oval(-20, -170, 3, 3, 'white')
  oval(17, -170, 3, 3, 'white')
  oval(0, -139, 10, 7, ink)
  line(ink, 3.4, p => { p.moveTo(-16, -126); p.quadraticCurveTo(0, -107, 16, -126) })
  oval(0, -121, 4, 4, '#fffaf3')
  oval(-41, -138, 8, 4, '#edab8d')
  oval(41, -138, 8, 4, '#edab8d')

  if (avatar.glasses !== 'none') {
    line('#203862', 3.6, p => {
      for (const x of [-22, 22]) {
        if (avatar.glasses === 'round') { p.moveTo(x + 18, -164); p.arc(x, -164, 18, 0, Math.PI * 2) }
        else if (typeof p.roundRect === 'function') p.roundRect(x - 17, -180, 34, 32, 6)
        else p.rect(x - 17, -180, 34, 32)
      }
      p.moveTo(-4, -166); p.lineTo(4, -166)
    })
  }

  const cap = capColors[avatar.headwear]
  if (cap) {
    const [base, visor, stitch] = cap
    oval(0, -204, 50, 26, base)
    oval(19, -188, 44, 9, visor, 0.052)
    line(stitch, 3, p => { p.moveTo(-9, -225); p.quadraticCurveTo(5, -215, 8, -199) })
    if (avatar.headwear === 'moon_cap') {
      oval(-24, -208, 7, 7, stitch)
      oval(-21, -210, 6, 6, base)
    }
  } else if (avatar.headwear === 'helmet' || avatar.headwear === 'mint_helmet') {
    const mint = avatar.headwear === 'mint_helmet'
    oval(0, -203, 54, 33, mint ? '#236d68' : '#435f8a')
    oval(0, -211, 50, 24, mint ? '#58b4a1' : '#638abb')
    line('#d7ecfd', 4, p => { p.moveTo(-39, -196); p.lineTo(43, -196) })
  } else if (avatar.headwear === 'crown') {
    ctx.beginPath()
    ctx.moveTo(-38, -203)
    ctx.lineTo(-49, -232)
    ctx.lineTo(-23, -219)
    ctx.lineTo(0, -243)
    ctx.lineTo(23, -219)
    ctx.lineTo(49, -232)
    ctx.lineTo(38, -203)
    ctx.closePath()
    ctx.fillStyle = '#f4be49'
    ctx.fill()
    line('#9e5912', 3, p => { p.moveTo(-38, -203); p.quadraticCurveTo(0, -198, 38, -203) })
    oval(0, -218, 6, 7, '#b14761')
    oval(0, -220, 2, 2, '#fff1b9')
  }
  ctx.restore()
}
