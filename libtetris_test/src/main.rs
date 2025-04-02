use libtetris::{
    Piece, RotationState, TspinStatus, PieceState, FallingPiece, Board,
    find_moves, MovementMode, SpawnRule,
};
use serde::Deserialize;

#[derive(Deserialize)]
struct Input {
    piece: String,
}

#[derive(serde::Serialize)]
struct Output {
    x: i32,
    y: i32,
    rotation: u8,
}

fn main() {
    let input_data = std::fs::read_to_string("input.json").expect("failed to read input.json");
    let input: Input = serde_json::from_str(&input_data).expect("invalid JSON");

    let piece = match input.piece.as_str() {
        "I" => Piece::I,
        "O" => Piece::O,
        "T" => Piece::T,
        "S" => Piece::S,
        "Z" => Piece::Z,
        "J" => Piece::J,
        "L" => Piece::L,
        _ => panic!("Unknown piece type"),
    };

    let board = Board::new();

    // Use SpawnRule to create the piece in a valid spawn location
    let falling_piece = SpawnRule::Row19Or20
        .spawn(piece, &board)
        .expect("Failed to spawn piece");

    let placements = find_moves(&board, falling_piece, MovementMode::ZeroG);

    let result: Vec<Output> = placements
        .iter()
        .map(|p| Output {
            x: p.location.x,
            y: p.location.y,
            rotation: p.location.kind.1 as u8,
        })
        .collect();

    println!("{}", serde_json::to_string_pretty(&result).unwrap());
}
