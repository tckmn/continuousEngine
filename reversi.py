from continuousEngine import *

# needs to be more than 1/sqrt(6)~=0.408 for diagonals to work the same as in the discreet game
piece_rad = .45

# squared distance
dist_sq = lambda p1,p2: (p1[0]-p2[0])**2+(p1[1]-p2[1])**2
# distance from the line p1-p2 to x
dist_to_line = lambda p1, p2, x: abs(p1[0]*p2[1]+p2[0]*x[1]+x[0]*p1[1]-p1[1]*p2[0]-p2[1]*x[0]-x[1]*p1[0]) / dist_sq(p1,p2)**.5
# is a piece centered at x on the path between pieces centered at p1 and p2?
in_path = lambda p1, p2, x: dist_to_line(p1, p2, x) < piece_rad and abs(dist_sq(p1,x)-dist_sq(p2,x)) < dist_sq(p1,p2)
# do pieces centered at p1 and p2 overlap?
overlap = lambda p1, p2: dist_sq(p1,p2) < (2*piece_rad)**2
# combat floating point errors. In particular, tangent circles shouldn't intersect
epsilon = 10**-10
# centers of circles tangent to both circles centered at p1 and p2
# (dx, dy) is the vector from the midpoint of p1 and p2 to one of the tangent circles
double_tangents = lambda p1, p2: (lambda d:
        (lambda dx, dy: ( ((p1[0]+p2[0])/2+dx*(1+epsilon),(p1[1]+p2[1])/2+dy*(1+epsilon)) , ((p1[0]+p2[0])/2-dx*(1+epsilon),(p1[1]+p2[1])/2-dy*(1+epsilon)) ))
        (((4*piece_rad**2-d/4))**.5*(p2[1]-p1[1])/d**.5,
         ((4*piece_rad**2-d/4))**.5*(p1[0]-p2[0])/d**.5 )
    if 0<d**.5 < 4*piece_rad else ())(dist_sq(p1,p2))
# centers of some circles tangent to circle centered at x on opposite sides,
#   such that one intersects the line from p1 to p2 in each region of angles such a tangent circle can intersect the line
# if the circle intersects the line, gives one on each side in the direction parallel to the line
# if the circle doesn't intersect the line, gives one on each side in the direction perpendicular to the line
# if the circle is far away, gives nothing
# (dx, dy) is a vector of length 2*piece_rad parallel to the line
on_line_tangents = lambda p1, p2, x: (lambda d:
        (lambda dx, dy: ( (x[0]+dx*(1+epsilon),x[1]+dy*(1+epsilon)) , (x[0]-dx*(1+epsilon),x[1]-dy*(1+epsilon)) ) )
            (2*piece_rad*(p2[0]-p1[0])/dist_sq(p1,p2)**.5,2*piece_rad*(p2[1]-p1[1])/dist_sq(p1,p2)**.5) if d < 1 else
        (lambda dx, dy: ( (x[0]+dy*(1+epsilon),x[1]-dx*(1+epsilon)) , (x[0]-dy*(1+epsilon),x[1]+dx*(1+epsilon)) ) )
            (2*piece_rad*(p2[0]-p1[0])/dist_sq(p1,p2)**.5,2*piece_rad*(p2[1]-p1[1])/dist_sq(p1,p2)**.5) if d < 3 else
        ()
    )(dist_to_line(p1,p2,x)/piece_rad)
# set of pieces which cause lines to flip if player t (str) places a piece at pt ((float,float)) given pieces pcs ([ReversiPiece])
# THE RULE: a piece at P is a "pivot" for your move M if
#               1. P is on your team
#               2. there's at least one piece, and only pieces on the opposite team, intersecting the line segment PM
#               3. the line segment PM is "filled" in the following sense:
#                   there is nowhere you could place another piece so it intersects PM but doesn't intersect any existing pieces
# this takes too long for more than ~20 pieces
# 1 and 2 are checked by the first three clauses of the if (before the lambda)
# 3 is the hard one. To check it, we try a particular set of potential placements such that (I've convinced myself) if none of them work, then nothing does
#   these potential placements are:
#       3.1. tangent to one existing piece in a particular direction (on_line_tangents). each piece close to the line gives 2 of these
#               the direction is parallel to the line if the piece intersects it, and perpendicular otherwise
#       3.2. tangent to two existing pieces (double_tangents). each pair of existing pieces gives 0 or 2 of these depending on their distance
# this takes O(n^3) time for n pieces, since we get at most 2 potential placements from double_tangents for each pair of pieces,
#   and check whether each potential placement intersects each piece
# we save some time by only considering pieces close enough to the line to matter (i.e. within 3*piece_rad)
# it's slowest when finding real pivots, since it has to check every potential location (and can be lazy when it fails to find a pivot)
# I don't know of a way to significantly reduce the number of attempted locations
# there are pathological cases meaning you can't just look at pieces on the line or something clever like that
# some testing confirms that the slow part is checking double tangencies (3.1). that should be O(n^3), and 3.2 should be O(n^2)
# I feel like people say "quadtree" to solve similar problems, but I don't really know how to use those and it sounds like a lot of work
# I could try spatially binning pieces (have a separate list for each 2x2 square, say) and only looking at the pieces in the nearby bins
pivots = lambda pcs, t, pt: {
    pv for pv in pcs 
        if pv.team==t # 1. pv is on right team
            and any(in_path(pt, (pv.x,pv.y), (p.x,p.y)) for p in pcs) # 2. there's a piece on the line
            and all(p.team !=t or not in_path(pt, (pv.x,pv.y), (p.x,p.y)) for p in pcs) # 2. there are only opposite-team pieces
            and (lambda closePieces: # 3. you can't fit another piece on the line without overlap: try some potential locations
                    # 3.1. tangent to one piece, in the direction (parrallel|perpendicular) to the line
                    all(not in_path(pt, (pv.x,pv.y), p) or any(overlap(p,(q.x,q.y)) for q in closePieces) or overlap(p,pt) for p1 in closePieces for p in on_line_tangents(pt, (pv.x,pv.y), (p1.x,p1.y)))
                    # 3.2. tangent to two pieces
                and all(not in_path(pt, (pv.x,pv.y), p) or any(overlap(p,(q.x,q.y)) for q in closePieces) or overlap(p,pt) for p1 in closePieces for p2 in closePieces for p in double_tangents((p1.x,p1.y),(p2.x,p2.y)))
            ) ([p for p in pcs if dist_to_line(pt, (pv.x,pv.y), (p.x,p.y)) < 3*piece_rad]) # save time by only looking at pieces nearish the line
}

printr = lambda x: (print(x),x)[1]


inc_turn = {'WHITE':'BLACK', 'BLACK':'WHITE'}

class Layers:
    GUIDES      = 2
    PIECES      = 3
    NEWPIECE    = 4

class Colors:
    fill        = {'WHITE': (255,255,255), 'BLACK': (0,  0,  0  )}
    border      = {'WHITE': (40, 40, 40 ), 'BLACK': (215,215,215)}
    flipper     = (0,255,0)
    blocker     = (255,0,0)
    guide       = (0,0,255)
    pivot       = (0,255,255)
    newborder   = (255,100,100)

class ReversiPiece(BorderDisk):
    def __init__(self, game, team, x, y, layer=Layers.PIECES):
        super().__init__(game, layer, None, None, x, y, piece_rad)
        self.team = team
        self.GETfill_color      = lambda g: Colors.fill[self.team]
        self.GETborder_color    = lambda g: Colors.blocker if self in g.blockers else Colors.flipper if self in g.flippers else Colors.border[self.team]

class ReversiGuide(Segment):
    def __init__(self, game, piece):
        super().__init__(game, Layers.GUIDES, Colors.guide, (piece.x, piece.y), None)
        self.piece = piece
        self.GETvisible = lambda g: g.mousePos and g.turn == self.piece.team and self.piece in g.pivots
        self.GETp2 = lambda g: g.mousePos

start_state = ('WHITE',[
    ('WHITE', .5, .5),
    ('WHITE',-.5,-.5),
    ('BLACK', .5,-.5),
    ('BLACK',-.5, .5),
])

game = Game(
    initialState=start_state,
    backgroundColor=(128,128,128)
)

game.mousePos = None
game.makePiece = lambda t, x, y: ReversiGuide(game, ReversiPiece(game, t, x, y))

nextPiece = ReversiPiece(game, None, None, None, Layers.NEWPIECE)
nextPiece.GETteam = lambda g: g.turn
nextPiece.GETvisible = lambda g: g.mousePos
nextPiece.GETx = lambda g: g.mousePos[0]
nextPiece.GETy = lambda g: g.mousePos[1]
nextPiece.border_color = Colors.newborder

game.save_state = lambda: (game.turn, [(p.team, p.x, p.y) for p in game.layers[Layers.PIECES]])
game.load_state = lambda x: (lambda turn, pieces:(
    game.clearLayer(Layers.PIECES),
    game.clearLayer(Layers.GUIDES),
    [game.makePiece(*p) for p in pieces],
    setattr(game, 'flippers', set()),
    setattr(game, 'blockers', set()),
    setattr(game, 'pivots', set()),
    setattr(game, 'turn', turn),
    ))(*x)


game.load_state(start_state)

def attemptMove(game, pos):
    updateMove(game, pos)
    if game.blockers: return
    if not game.pivots: return
    
    game.record_state()
    game.makePiece(game.turn, *pos)
    for p in game.flippers: p.team = inc_turn[p.team]
    game.turn = inc_turn[game.turn]

def updateMove(game, pos):
    game.blockers = {p for p in game.layers[Layers.PIECES] if overlap(pos, (p.x,p.y))}
    game.pivots = pivots(game.layers[Layers.PIECES], game.turn, pos)
    game.flippers = {p for p in game.layers[Layers.PIECES] if any(in_path(pos, (pv.x,pv.y), (p.x,p.y)) for pv in game.pivots)}
    game.mousePos = pos

# test speed:
if 0:
    import random
    spread = 5
    count = 30
    [game.makePiece(random.choice(['WHITE','BLACK']),random.random()*spread,random.random()*spread) for _ in range(count)]

game.click[1] = lambda e: attemptMove(game, game.point(*e.pos))
game.drag[-1] = lambda e: updateMove(game, game.point(*e.pos))

while 1: game.update()