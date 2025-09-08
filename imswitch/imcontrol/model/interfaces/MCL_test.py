import MCL_microdrive_iscat as md

if __name__ == '__main__':
    driver = md.MicroDrive()
    #driver.EncodersReset()
    print(driver.getPosition())
    print(driver.getStatus())
    x = float(input())
    pos = driver.moveCoordinate(x)

    print("moving home")
    print(driver.home())