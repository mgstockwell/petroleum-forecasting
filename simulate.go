package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"math/rand"
	"os"
	"strconv"
	"sync"
	"time"
)

type Params struct {
	S0               float64 `json:"s0"`
	SigmaCrude       float64 `json:"sigma_crude"`
	JumpLambda       float64 `json:"jump_lambda"`
	JumpMu           float64 `json:"jump_mu"`
	CrackGas0        float64 `json:"crack_gas_0"`
	CrackDiesel0     float64 `json:"crack_diesel_0"`
	SigmaCrackGas    float64 `json:"sigma_crack_gas"`
	SigmaCrackDiesel float64 `json:"sigma_crack_diesel"`
}

const (
	Days  = 180
	Sims  = 10000
	Dt    = 1.0 / 365.0
	Mu    = 0.05
	TaxG  = 0.57
	DistG = 0.65
	TaxD  = 0.65
	DistD = 0.85
)

func main() {
	seed := time.Now().UnixNano()

	file, err := os.Open("params.json")
	if err != nil {
		panic("Run calibrate.py first to generate params.json")
	}
	defer file.Close()

	var p Params
	if err := json.NewDecoder(file).Decode(&p); err != nil {
		log.Fatalf("failed to decode params.json: %v", err)
	}

	var wg sync.WaitGroup
	gasResults := make([][]string, Sims)
	dieselResults := make([][]string, Sims)

	fmt.Println("Running 10,000 parallel paths...")
	for i := 0; i < Sims; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			rng := rand.New(rand.NewSource(seed + int64(idx)))

			st := p.S0
			cGas := p.CrackGas0
			cDies := p.CrackDiesel0

			gasPath := make([]string, Days)
			diesPath := make([]string, Days)

			for t := 0; t < Days; t++ {
				z := rng.NormFloat64()

				jumpShock := 0.0
				if rng.Float64() < (p.JumpLambda * Dt) {
					jumpShock = math.Exp(rng.NormFloat64()*0.05+p.JumpMu) - 1.0
				}

				dS := Mu*st*Dt + p.SigmaCrude*st*math.Sqrt(Dt)*z + jumpShock*st
				st += dS

				cGas += rng.NormFloat64() * p.SigmaCrackGas * 0.1
				cDies += rng.NormFloat64() * p.SigmaCrackDiesel * 0.1

				gasPrice := (st / 42.0) + (cGas / 42.0) + TaxG + DistG
				diesPrice := (st / 42.0) + (cDies / 42.0) + TaxD + DistD

				gasPath[t] = strconv.FormatFloat(gasPrice, 'f', 2, 64)
				diesPath[t] = strconv.FormatFloat(diesPrice, 'f', 2, 64)
			}
			gasResults[idx] = gasPath
			dieselResults[idx] = diesPath
		}(i)
	}
	wg.Wait()

	if err := writeCSV("results_gas.csv", gasResults); err != nil {
		log.Fatalf("failed to write gas results: %v", err)
	}
	if err := writeCSV("results_diesel.csv", dieselResults); err != nil {
		log.Fatalf("failed to write diesel results: %v", err)
	}
	fmt.Println("Simulation complete. Output saved to CSVs.")
}

func writeCSV(filename string, data [][]string) error {
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()
	writer := csv.NewWriter(file)
	defer writer.Flush()
	writer.WriteAll(data)
	return writer.Error()
}
