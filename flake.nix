{
  description = "Lightweight endpoints for serving owt yer like";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      {
        devShells = {
          default = nixpkgs.legacyPackages.${system}.callPackage ./shell.nix { };
        };
        packages = {
          default = nixpkgs.legacyPackages.${system}.callPackage ./default.nix { };
        };
      });
}
