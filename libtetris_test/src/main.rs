use libtetris::{
    Piece, RotationState, TspinStatus, PieceState, FallingPiece, Board,
    find_moves, MovementMode, SpawnRule,
};
use enumset::EnumSet;
use serde::Deserialize;

#[derive(Deserialize)]
struct Input {
    piece: String,
    field: Vec<Vec<u8>>,     // 40 rows × 10 columns, bottom to top
    bag: Vec<String>,        // Remaining 7-bag pieces
    hold: Option<String>,    // Hold piece, or null
    b2b: bool,
    combo: u32,
}

#[derive(serde::Serialize)]
struct Output {
    x: i32,
    y: i32,
    rotation: u8,
    inputs: Vec<String>,
    tspin: String,
}

fn parse_piece(s: &str) -> Piece {
    match s {
        "I" => Piece::I,
        "O" => Piece::O,
        "T" => Piece::T,
        "S" => Piece::S,
        "Z" => Piece::Z,
        "J" => Piece::J,
        "L" => Piece::L,
        _ => panic!("Unknown piece type: {}", s),
    }
}

fn main() {
    let input_data = std::fs::read_to_string("input.json").expect("failed to read input.json");
    let input: Input = serde_json::from_str(&input_data).expect("invalid JSON");

    // Convert board field
    let mut field = [[false; 10]; 40];
    for (y, row) in input.field.iter().enumerate().take(40) {
        for (x, val) in row.iter().enumerate().take(10) {
            field[y][x] = *val != 0;
        }
    }

    // Convert bag
    let bag: EnumSet<Piece> = input.bag.iter().map(|s| parse_piece(s)).collect();

    // Convert hold piece
    let hold_piece = input.hold.map(|s| parse_piece(&s));

    // Create board with full state
    let board = Board::new_with_state(field, bag, hold_piece, input.b2b, input.combo);

    // Active piece
    let piece = parse_piece(&input.piece);

    // Spawn piece
    let falling_piece = SpawnRule::Row19Or20
        .spawn(piece, &board)
        .expect("Failed to spawn piece");

    // Find placements
    let placements = find_moves(&board, falling_piece, MovementMode::ZeroG);

    let result: Vec<Output> = placements
        .iter()
        .map(|p| Output {
            x: p.location.x,
            y: p.location.y,
            rotation: p.location.kind.1 as u8,
            inputs: p.inputs.movements.iter().map(|m| format!("{:?}", m)).collect(),
            tspin: format!("{:?}", p.location.tspin),
        })
        .collect();

    println!("{}", serde_json::to_string_pretty(&result).unwrap());
}
