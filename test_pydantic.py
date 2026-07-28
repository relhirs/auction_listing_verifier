from pydantic import BaseModel, ValidationError

class Vehicle(BaseModel):
    make: str
    model: str
    vin: str
    year: int
    mileage: int
    color: str
    
def main():
    print("Testing valid data")
    valid_car = Vehicle (
        make = "Toyota",
        model = "supra",
        vin = "1GCHC33J0CZ102544",
        year = 1990,
        mileage = 110980,
        color = "black"    
    )
    
    print("Successfully created vehicle")
    print(valid_car)
    
    print("\nExported as a dictionary")
    print(valid_car.model_dump())
    
    print("Testing invalid data")
    try:
        invalid_car = Vehicle (
            make = "Ford",
            model = "F-150",
            vin = "1FD7X3F65JEB42562",
            year = "twenty twenty five",
            mileage = 1550,
            color = "white"
        )
    except ValidationError as e:
        print("Invalid. Pydantic caught following errors: \n")
        print(e)
        
if __name__ == "__main__":
    main()

            
        