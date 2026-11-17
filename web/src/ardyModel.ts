import {
  BufferGeometry, CatmullRomCurve3, Float32BufferAttribute, Group, LineCurve3, Mesh,
  MeshStandardMaterial, SphereGeometry, TorusGeometry, TubeGeometry, Vector3,
  type Material,
} from 'three'
import { capColors, jacketColors, palettes, type Avatar } from './ardy'

type Position = [number, number, number]

function sculptTail(fluffy: boolean) {
  const path = new CatmullRomCurve3([
    new Vector3(0, .57, -.35), new Vector3(.57, .74, -.82),
    new Vector3(1.02, 1.25, -.96), new Vector3(1.07, 1.85, -.94),
    new Vector3(.78, 2.28, -.88), new Vector3(.37, 2.30, -.80),
    new Vector3(.17, 2.01, -.74),
  ])
  const rings = 40
  const facets = 24
  const frame = path.computeFrenetFrames(rings, false)
  const vertices: number[] = []
  const indices: number[] = []
  const point = new Vector3()
  for (let ring = 0; ring <= rings; ring++) {
    const progress = ring / rings
    const center = path.getPointAt(progress)
    const volume = Math.sin(Math.PI * progress) ** .78
    const radius = .16 * (1 - progress) + (fluffy ? .51 : .36) * volume + .008
    for (let side = 0; side < facets; side++) {
      const angle = side * 2 * Math.PI / facets
      point.copy(center)
        .addScaledVector(frame.normals[ring]!, Math.cos(angle) * radius)
        .addScaledVector(frame.binormals[ring]!, Math.sin(angle) * radius)
      vertices.push(point.x, point.y, point.z)
      if (ring === rings) continue
      const a = ring * facets + side
      const b = ring * facets + (side + 1) % facets
      indices.push(a, b, a + facets, b, b + facets, a + facets)
    }
  }
  const geometry = new BufferGeometry()
  geometry.setAttribute('position', new Float32BufferAttribute(vertices, 3))
  geometry.setIndex(indices)
  geometry.computeVertexNormals()
  return geometry
}

export function buildArdy(avatar: Avatar) {
  const model = new Group()
  const sphere = new SphereGeometry(1, 24, 16)
  const colors = new Map<string, MeshStandardMaterial>()
  const [fur, shade, cream] = palettes[avatar.fur] ?? palettes.amber!
  const ink = '#292643'
  const shoulder = avatar.build === 'athletic' ? .55 : .46
  const waist = { slender: .4, rounded: .52, athletic: .46 }[avatar.build] ?? .52
  const hood = ['hoodie', 'sage_hoodie'].includes(avatar.outfit)
  const [cloth, trim] = jacketColors[avatar.outfit] ?? (avatar.outfit === 'sage_hoodie'
    ? ['#537d64', '#b3d0b2'] : hood ? ['#245daf', '#a7cdff'] : ['#263f72', '#8dc5f8'])
  const dressed = avatar.outfit !== 'none'

  function mesh(geometry: BufferGeometry, color: string) {
    let material = colors.get(color)
    if (!material) {
      material = new MeshStandardMaterial({ color, roughness: .58 })
      colors.set(color, material)
    }
    const part = new Mesh(geometry, material)
    model.add(part)
    return part
  }

  function oval(position: Position, scale: Position, color: string, tilt = 0) {
    const part = mesh(sphere, color)
    part.position.set(...position)
    part.scale.set(...scale)
    part.rotation.z = tilt
    return part
  }

  function stroke(points: Position[], radius: number, color: string) {
    const vectors = points.map(point => new Vector3(...point))
    const path = vectors.length === 2 ? new LineCurve3(vectors[0]!, vectors[1]!) : new CatmullRomCurve3(vectors)
    mesh(new TubeGeometry(path, vectors.length * 4, radius, 6), color)
  }

  mesh(sculptTail(avatar.tail === 'fluffy'), shade)
  oval([0, .85, 0], [waist, .62, .39], dressed ? cloth : fur)
  if (!dressed) oval([0, .80, .26], [waist * .7, .43, .17], cream)
  for (const side of [-1, 1]) {
    oval([side * shoulder, .88, .02], [.18, .36, .19], dressed ? cloth : fur, .38 * side)
    oval([side * (shoulder + .08), .59, .14], [.14, .17, .15], fur, .26 * side)
    oval([side * .26, .18, .20], [.24, .17, .33], shade, side * -.12)
    oval([side * .27, .19, .41], [.17, .12, .15], fur)
  }

  if (hood) {
    oval([0, 1.32, -.10], [waist, .24, .40], cloth)
    for (const side of [-1, 1]) {
      stroke([[side * .15, 1.26, .29], [side * .18, 1.09, .37], [side * .18, .98, .38]], .02, trim)
    }
    stroke([[-.24, .68, .34], [0, .63, .39], [.24, .68, .34]], .016, trim)
  } else if (dressed) {
    stroke([[0, 1.32, .28], [0, .98, .381], [0, .67, .386], [0, .39, .25]], .021, trim)
    oval([.22, .99, .35], [.073, .075, .025], trim, -.12)
    if (avatar.outfit === 'nebula_jacket') {
      oval([-.23, .95, .34], [.025, .025, .019], trim)
      oval([-.30, .85, .31], [.019, .019, .014], trim)
    }
  }

  if (avatar.accessory === 'chain') {
    stroke([[-.31, 1.29, .25], [-.23, 1.13, .365], [0, 1.04, .406], [.23, 1.13, .365], [.31, 1.29, .25]], .024, '#e6ba50')
    oval([0, 1.01, .415], [.059, .069, .03], '#ffdf7b')
  } else if (avatar.accessory === 'backpack') {
    oval([0, .91, -.42], [.36, .44, .2], '#6e55a1')
    oval([0, .82, -.56], [.23, .23, .11], '#a28bd1')
    for (const side of [-1, 1]) {
      stroke([[side * .26, 1.22, -.47], [side * .30, 1.33, .14], [side * .30, 1.04, .31], [side * .34, .72, .23]], .042, '#674e97')
    }
  }

  oval([0, 1.84, .02], [.63, .58, .49], fur)
  for (const side of [-1, 1]) {
    const ear = side * .44
    oval([ear, 2.28, -.03], [.24, .32, .16], shade, -.31 * side)
    oval([ear, 2.30, .093], [.148, .215, .059], cream, -.31 * side)
    oval([side * .19, 1.63, .377], [.32, .231, .191], cream, side * .16)
    oval([side * .405, 1.68, .477], [.078, .032, .024], '#edab8d', side * .15)
    const eye = side * .224
    oval([eye, 1.90, .431], [.154, .21, .11], '#fffaf3')
    oval([eye - side * .015, 1.897, .514], [.090, .133, .056], ink)
    oval([eye - .041, 1.946, .561], [.033, .037, .015], '#ffffff')
  }
  oval([0, 1.698, .565], [.105, .066, .056], ink)
  stroke([[-.138, 1.57, .546], [0, 1.525, .568], [.138, 1.57, .546]], .017, ink)
  oval([0, 1.56, .565], [.043, .041, .015], '#fffaf3')

  if (avatar.texture !== 'smooth') {
    for (const side of [-1, 0, 1]) {
      const x = side * .135
      if (avatar.texture === 'curly') {
        const curl = mesh(new TorusGeometry(.047, .018, 6, 14, Math.PI * 1.65), shade)
        curl.position.set(x, 2.221 + .027 * (1 - Math.abs(side)), .368)
        curl.rotation.z = side * .37
      } else {
        stroke([[x - .058, 2.213, .377], [x - .014, 2.252, .354], [x + .059, 2.226, .37]], .021, shade)
      }
    }
  }

  if (avatar.glasses !== 'none') {
    const frame = '#203862'
    for (const x of [-.224, .224]) {
      if (avatar.glasses === 'round') {
        const lens = mesh(new TorusGeometry(.187, .023, 8, 32), frame)
        lens.position.set(x, 1.913, .547)
        lens.scale.y = 1.16
      } else {
        stroke([[x - .18, 1.76, .547], [x - .18, 2.06, .547], [x + .18, 2.06, .547],
          [x + .18, 1.76, .547], [x - .18, 1.76, .547]], .023, frame)
      }
      stroke([[x * 1.83, 1.95, .547], [x * 2.3, 1.96, .26]], .021, frame)
    }
    stroke([[-.052, 1.937, .548], [.052, 1.937, .548]], .024, frame)
  }

  const cap = capColors[avatar.headwear]
  if (cap) {
    const [base, visor, stitch] = cap
    oval([0, 2.24, .04], [.53, .29, .43], base)
    oval([.04, 2.16, .43], [.50, .062, .33], visor, -.08)
    oval([0, 2.526, .035], [.058, .034, .06], visor)
    oval([-.12, 2.333, .432], [.053, .057, .022], stitch)
  } else if (['helmet', 'mint_helmet'].includes(avatar.headwear)) {
    const mint = avatar.headwear === 'mint_helmet'
    oval([0, 2.255, .01], [.568, .32, .48], mint ? '#58b4a1' : '#638abb')
    oval([0, 2.125, .03], [.568, .095, .49], mint ? '#236d68' : '#435f8a')
    oval([0, 2.406, .322], [.09, .13, .077], '#d7ecfd')
  } else if (avatar.headwear === 'crown') {
    const gold = '#f4be49'
    const band = mesh(new TorusGeometry(.36, .071, 10, 30), gold)
    band.position.set(0, 2.328, .025)
    band.rotation.x = Math.PI / 2
    for (let spike = 0; spike < 6; spike++) {
      const angle = spike * Math.PI / 3
      oval([.35 * Math.sin(angle), spike % 2 ? 2.45 : 2.51, .025 + .35 * Math.cos(angle)],
        [.073, spike % 2 ? .14 : .194, .065], gold)
    }
    oval([0, 2.476, .435], [.049, .066, .032], '#b14761')
  }

  model.scale.y = avatar.height / 100
  return model
}

export function disposeArdy(group: Group) {
  const geometries = new Set<BufferGeometry>()
  const materials = new Set<Material>()
  group.traverse(part => {
    if (!(part instanceof Mesh)) return
    geometries.add(part.geometry)
    materials.add(part.material)
  })
  geometries.forEach(geometry => geometry.dispose())
  materials.forEach(material => material.dispose())
}
